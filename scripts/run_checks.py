"""Run reproducible local tests with fresh ephemeral keys and explicit DB skips."""
from pathlib import Path
import argparse,inspect,os,secrets,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=('security','unit'),default='security')
    args=parser.parse_args()
    os.environ['AUTH_TOKEN_SECRET']=secrets.token_urlsafe(48)
    os.environ['DATABASE_URL']=os.environ.get('TEST_DATABASE_URL','')
    os.environ['OLLAMA_EMBEDDING_MODEL']='bge-m3:latest'
    sys.path.insert(0,str(ROOT/'dcm-back'))
    with tempfile.TemporaryDirectory(prefix='complaintai-check-') as directory:
        os.environ['FILE_STORAGE_DIR']=directory
        os.chdir(ROOT/'dcm-back')
        loader=unittest.TestLoader()
        if args.suite=='security':
            suite=loader.discover('tests',pattern='test_publication_security.py')
            suite.addTests(loader.discover('tests',pattern='test_unit_plan_contracts.py'))
            suite.addTests(loader.discover('tests',pattern='test_chat_complaint_scope.py'))
        else:
            suite=loader.discover('tests',pattern='test_*.py')
            if not os.environ.get('TEST_DATABASE_URL'):
                marked=set()
                for case in flatten(suite):
                    cls=type(case)
                    if cls in marked:continue
                    marked.add(cls)
                    try:setup=inspect.getsource(cls.setUpClass)
                    except (TypeError,OSError):continue
                    if 'psycopg.connect' in setup:
                        unittest.skip('TEST_DATABASE_URL not provided; disposable PostgreSQL/pgvector DB required')(cls)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
