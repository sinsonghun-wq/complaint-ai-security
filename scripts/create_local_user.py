"""Create one local account without shared credentials or command-line passwords."""
from pathlib import Path
import argparse,getpass,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dcm-back'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',required=True)
    parser.add_argument('--name',default='')
    parser.add_argument('--department-id',type=int,help='부서 관리자일 때 실제 departments.id')
    args=parser.parse_args()
    username=args.username.strip()
    if not 3<=len(username)<=30 or not username.replace('_','').replace('-','').isalnum():
        parser.error('username은 영문/숫자/한글/밑줄/하이픈 3~30자입니다.')
    password=getpass.getpass('새 로컬 비밀번호 (12자 이상): ')
    confirm=getpass.getpass('비밀번호 확인: ')
    if len(password)<12 or password!=confirm:
        parser.error('비밀번호 길이 또는 확인 값이 올바르지 않습니다.')
    from app.security import password_hash,uuid4
    from app.db import connection
    salt,digest=password_hash(password)
    role='admin' if args.department_id is not None else 'user'
    with connection() as db:
        if args.department_id is not None and not db.execute('SELECT id FROM departments WHERE id=%s',(args.department_id,)).fetchone():
            parser.error('존재하는 department ID를 지정하세요.')
        db.execute('''INSERT INTO app_users(id,owner_id,email,username,display_name,password_salt,password_hash,account_role,department_id)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(uuid4(),uuid4(),username+'@complaintai.local',username,args.name.strip() or username,salt,digest,role,args.department_id))
    print('로컬 계정을 생성했습니다. 비밀번호와 해시는 출력하지 않습니다.')

if __name__=='__main__':main()
