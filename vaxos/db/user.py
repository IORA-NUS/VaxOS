from peewee import *
import os


dir_path = os.path.dirname(os.path.realpath(__file__))
db = SqliteDatabase(f'{dir_path}/vaxos.sqlite.db')

class User(Model):

    scenario_name = CharField()
    init_date = DateTimeField()
    history = CharField()
    current = CharField()
    status = CharField()

    class Meta:
        database = db
