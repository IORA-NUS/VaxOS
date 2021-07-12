from peewee import *
import os

from vaxos.db.status import Status
from vaxos.db.file_upload import FileUpload

dir_path = os.path.dirname(os.path.realpath(__file__))
db = SqliteDatabase(f'{dir_path}/vaxos.sqlite.db')


def create_tables():
    with db:
        try:
            db.drop_tables([Status, FileUpload])
        except Exception as e:
            print(e)

        db.create_tables([Status, FileUpload])

def clear_db_history():
    Status.delete().where(Status.status != 'In Progress').execute()
    FileUpload.delete().where(FileUpload.status != 'In Progress').execute()

def purge_db_history():
    Status.delete().execute()
    FileUpload.delete().execute()

if __name__ == "__main__":
    create_tables()
