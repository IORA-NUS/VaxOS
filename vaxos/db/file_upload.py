from peewee import *
import os


dir_path = os.path.dirname(os.path.realpath(__file__))
db = SqliteDatabase(f'{dir_path}/vaxos.sqlite.db')


class FileUpload(Model):

    file_name = CharField()
    processing_date = DateTimeField()
    status = CharField()

    class Meta:
        database = db

