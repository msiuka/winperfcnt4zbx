from peewee import *
import os

dbpath = os.path.join(os.path.dirname(__file__), 'mssqlix.db')
db = SqliteDatabase(dbpath)

# Name for not founded instances in db
EMPTY_INSTANCE_TEXT_REPRESENTATION = "Other counters"


class MSSQLixModel(Model):
    class Meta:
        database = db

    @classmethod
    def init_db(cls):
        db.connect()
        db.create_tables(MSSQLixModel.__subclasses__())

    @classmethod
    def close_db(cls):
        db.close()

    @classmethod
    def clear_db(cls):
        db.drop_tables(MSSQLixModel.__subclasses__())
        db.create_tables(MSSQLixModel.__subclasses__())

    @classmethod
    def save_form_data(cls, formdata, filter):
        for fieldname in formdata:
            if filter in fieldname:
                db_rec = cls.get_by_id(int(fieldname.replace(filter + '_', '')))
                db_rec.checked = formdata[fieldname]
                db_rec.save()


class Instances(MSSQLixModel):
    name = CharField()
    delimeter = CharField(default="")


class CounterGroup(MSSQLixModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = CharField(default="")
    instance_id = ForeignKeyField(Instances, null=True, backref='instancesandgroups')


class Counters(MSSQLixModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    counter_group_id = ForeignKeyField(CounterGroup, backref='countersandgroups')
    description = CharField(default="")
    checked = BooleanField(default=False)


class Parameters(MSSQLixModel):
    name = CharField()
    counter_group_id = ForeignKeyField(CounterGroup, backref='paramsandcounters')
    checked = BooleanField(default=False)


class MSSQLixQueries:

    @staticmethod
    def get_checked_counters_and_parameters():
        subquery = (Counters.select(fn.COUNT(Counters.id).alias('checked_cnt'), Counters.counter_group_id)
                    .group_by(Counters.counter_group_id)
                    .where(Counters.checked == 1)
                    )

        query = (CounterGroup
                 .select()
                 .join(subquery, on=(
                (subquery.c.checked_cnt > 0) &
                (subquery.c.counter_group_id == CounterGroup.id)
        ))
                 )

        selected_data = {}
        for cnt_group in query:
            instance = Instances.get_by_id(cnt_group.instance_id)
            inst_with_delmtr = instance.name + instance.delimeter
            if selected_data.get(inst_with_delmtr) is None:
                selected_data.update({inst_with_delmtr: {}})
            if selected_data.get(inst_with_delmtr).get(cnt_group.name) is None:
                selected_data[inst_with_delmtr].update({cnt_group.name: {
                    'id': cnt_group.id,
                    'counters': [],
                    'parameters': []
                }})

            cnt_query = Counters.select().where(
                (Counters.counter_group_id == cnt_group.id) & (Counters.checked == True)
            )
            prm_query = Parameters.select().where(
                (Parameters.counter_group_id == cnt_group.id) & (Parameters.checked == True)
            )

            for cnt in cnt_query:
                selected_data[inst_with_delmtr][cnt_group.name]['counters'].append((cnt.name, cnt.id))

            for prm in prm_query:
                selected_data[inst_with_delmtr][cnt_group.name]['parameters'].append(prm.name)

        return selected_data
