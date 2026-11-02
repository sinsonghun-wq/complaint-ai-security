"""Security regression tests use synthetic values and never connect to an app DB."""
import asyncio,base64,hashlib,hmac,json,os,secrets,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from fastapi import HTTPException,UploadFile
from fastapi.testclient import TestClient
from io import BytesIO
from app import ai,security
from app.dependencies import require_department_access
from app.main import app
from app.routers.complaints import react_app
from app.utils.util import save_upload

ROOT=Path(__file__).resolve().parents[2]

class AuthenticationSecurityTests(unittest.TestCase):
    def setUp(self):
        self.user={'id':'synthetic-user','owner_id':'synthetic-owner','account_role':'user','department_id':None}
    def signed(self,payload):
        body=security._b64(json.dumps(payload).encode())
        return body+'.'+security._b64(hmac.new(security.AUTH_TOKEN_SECRET.encode(),body.encode(),hashlib.sha256).digest())
    def test_valid_token_round_trip(self):
        self.assertEqual(security.read_token(security.issue_token(self.user))['owner_id'],'synthetic-owner')
    def test_unsigned_and_modified_role_are_rejected(self):
        token=security.issue_token(self.user)
        body,sig=token.split('.')
        raw=json.loads(security._unb64(body));raw['role']='admin'
        self.assertIsNone(security.read_token(security._b64(json.dumps(raw).encode())+'.'+sig))
        self.assertIsNone(security.read_token(body+'.unsigned'))
    def test_expired_token_is_rejected(self):
        self.assertIsNone(security.read_token(self.signed({'sub':'u','owner_id':'o','role':'user','exp':0})))
    def test_signed_malformed_claims_are_rejected(self):
        for raw in ([],{}, {'sub':'u','owner_id':'o','role':'root','exp':10**15}, {'sub':[],'owner_id':'o','role':'user','exp':10**15}):
            with self.subTest(kind=type(raw).__name__):self.assertIsNone(security.read_token(self.signed(raw)))
    def test_oversized_or_wrong_type_header_is_rejected(self):
        for raw in ('a'*9000,None,123,[], 'a.b.c'):
            self.assertIsNone(security.read_token(raw))
    def test_current_database_account_controls_role_and_owner(self):
        user={'id':'synthetic-user','owner_id':'current-owner','account_role':'user','department_id':None}
        forged_stale=security.issue_token({**self.user,'account_role':'admin','department_id':2})
        with patch.object(security,'current_account',return_value=user):
            result=security.actor_from_auth('Bearer '+forged_stale)
        self.assertEqual(result['role'],'user');self.assertEqual(result['owner_id'],'current-owner')
    def test_missing_or_example_signing_key_blocks_start(self):
        for value in ('','short','example-'+secrets.token_hex(30)):
            env={**os.environ,'AUTH_TOKEN_SECRET':value,'PYTHONPATH':str(ROOT/'dcm-back')}
            result=subprocess.run([sys.executable,'-c','import app.settings'],env=env,capture_output=True)
            self.assertNotEqual(result.returncode,0)
    def test_private_routes_require_authentication(self):
        client=TestClient(app)
        for url in ('/api/complaints','/api/departments','/api/auth/context','/api/trash/counts','/api/rag-imports/latest'):
            with self.subTest(url=url):self.assertEqual(client.get(url).status_code,401)
        client.close()
    def test_sql_injection_in_login_remains_a_bound_parameter(self):
        from app.routers.auth import login
        from app.models import LoginBody
        payload="' OR 1=1 --"
        with patch('app.routers.auth.fetch_one',return_value=None) as query:
            with self.assertRaises(HTTPException):login(LoginBody(username=payload,password='synthetic'))
        sql,params=query.call_args.args
        self.assertNotIn(payload,sql);self.assertEqual(params,(payload,))

class AccessAndPrivacyTests(unittest.TestCase):
    def test_department_admin_cannot_modify_other_department(self):
        with self.assertRaises(HTTPException) as exc:
            require_department_access({'role':'admin','department_id':1},{'department_id':2})
        self.assertEqual(exc.exception.status_code,403)
    def test_user_cannot_gain_admin_write_permission(self):
        with self.assertRaises(HTTPException):require_department_access({'role':'user','department_id':1},{'department_id':1})
    def test_identity_phone_and_email_are_fully_masked(self):
        # Synthetic identifiers only. Each full identifier must disappear.
        for text in ('900101-1234567','9001011234567','010-1234-5678','a.b@example.test'):
            with self.subTest(kind=len(text)):self.assertEqual(ai.redact(text),'[개인정보 제외]')
    def test_static_route_prevents_parent_and_absolute_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);static=folder/'dist';static.mkdir()
            (static/'index.html').write_text('index');(folder/'private.txt').write_text('private')
            with patch('app.routers.complaints.STATIC_DIR',static):
                for path in ('../private.txt',str(folder/'private.txt')):
                    with self.assertRaises(HTTPException) as exc:react_app(path,None)
                    self.assertEqual(exc.exception.status_code,404)
                self.assertEqual(Path(react_app('client/route',None).path),static/'index.html')
    def test_public_user_response_excludes_password_material(self):
        raw={'id':'u','owner_id':'o','username':'synthetic','account_role':'user','password_salt':'s','password_hash':'h'}
        public=security.public_user(raw)
        self.assertNotIn('password_salt',public);self.assertNotIn('password_hash',public)

class UploadSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_original_upload_name_cannot_choose_storage_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('app.utils.util.FILE_STORAGE_DIR',root):
                path,suffix=await save_upload(UploadFile(filename='../../private.csv',file=BytesIO(b'abc')),8)
            self.assertEqual(path.parent,root);self.assertEqual(suffix,'.csv');self.assertNotEqual(path.name,'private.csv')
    async def test_oversized_upload_is_rejected_and_partial_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('app.utils.util.FILE_STORAGE_DIR',root):
                with self.assertRaises(HTTPException) as exc:await save_upload(UploadFile(filename='x.csv',file=BytesIO(b'a'*20)),8)
            self.assertEqual(exc.exception.status_code,413);self.assertEqual(list(root.iterdir()),[])

class PublicationMaterialTests(unittest.TestCase):
    def test_service_bootstrap_contains_no_default_password_accounts(self):
        sql=(ROOT/'database/init.sql').read_text(encoding='utf-8')
        self.assertNotIn('INSERT INTO app_users',sql)
    def test_training_notebook_has_no_stored_execution_outputs(self):
        notebook=json.loads((ROOT/'model-training/colab_train.ipynb').read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            if cell['cell_type']=='code':self.assertEqual(cell.get('outputs'),[])
    def test_remote_model_revision_is_immutable(self):
        sys.path.insert(0,str(ROOT/'model-training'))
        import common
        for value in ('','main','v1','a'*39):
            with patch.dict(os.environ,{'BASE_MODEL_REVISION':value}):
                with self.assertRaises(ValueError):common.pinned_model_revision()
        with patch.dict(os.environ,{'BASE_MODEL_REVISION':'a'*40}):self.assertEqual(common.pinned_model_revision(),'a'*40)
    def test_model_eval_disallows_file_scheme(self):
        sys.path.insert(0,str(ROOT/'model-training'))
        import evaluate
        with self.assertRaises(ValueError):evaluate.open_http('file:///private.txt',timeout=1)
