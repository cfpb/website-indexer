from django.db import connections


class DatabaseWriter:
    def __init__(self, db):
        self.db = db
        self.connection = connections[self.db]
        self.connection.disable_constraint_checking()

        self.writers = {}

    def write(self, instance):
        instance_model = instance._meta.model

        if instance_model not in self.writers:
            self.writers[instance_model] = TableWriter(self.db, instance_model)

        writer = self.writers[instance_model]
        writer.write(instance)

    def flush(self):
        for writer in self.writers.values():
            writer.flush()

        with self.connection.cursor() as cursor:
            cursor.execute("ANALYZE")


class TableWriter:
    def __init__(self, db, model):
        self.db = db
        self.model = model

        self.records = list()
        self.chunk_size = 100

    def write(self, record):
        self.records.append(record)

        if len(self.records) >= self.chunk_size:
            self._do_insert()

    def flush(self):
        if self.records:
            self._do_insert()

    def _do_insert(self):
        self.model.objects.using(self.db).bulk_create(self.records)
        self.records.clear()
