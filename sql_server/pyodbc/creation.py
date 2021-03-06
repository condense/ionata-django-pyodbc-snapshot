from django.db.backends.creation import BaseDatabaseCreation
import base64
from django.utils.hashcompat import md5_constructor
import random

class DataTypesWrapper(dict):
    def __getitem__(self, item):
        if item in ('PositiveIntegerField', 'PositiveSmallIntegerField'):
            # The check name must be unique for the database. Add a random
            # component so the regresion tests don't complain about duplicate names
            fldtype = {'PositiveIntegerField': 'int', 'PositiveSmallIntegerField': 'smallint'}[item]
            rnd_hash = md5_constructor(str(random.random())).hexdigest()
            unique = base64.b64encode(rnd_hash, '__')[:6]
            return '%(fldtype)s CONSTRAINT [CK_%(fldtype)s_pos_%(unique)s_%%(column)s] CHECK ([%%(column)s] >= 0)' % locals()
        return super(DataTypesWrapper, self).__getitem__(item)

class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated MS SQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    #
    # Any format strings starting with "qn_" are quoted before being used in the
    # output (the "qn_" prefix is stripped before the lookup is performed.

    data_types = DataTypesWrapper({
    #data_types = {
        'AutoField':         'int IDENTITY (1, 1)',
        'BooleanField':      'bit',
        'CharField':         'nvarchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'nvarchar(%(max_length)s)',
        'DateField':         'datetime',
        'DateTimeField':     'datetime',
        'DecimalField':      'numeric(%(max_digits)s, %(decimal_places)s)',
        'FileField':         'nvarchar(%(max_length)s)',
        'FilePathField':     'nvarchar(%(max_length)s)',
        'FloatField':        'double precision',
        'IntegerField':      'int',
        'BigIntegerField':   'bigint',
        'IPAddressField':    'nvarchar(15)',
        'NullBooleanField':  'bit',
        'OneToOneField':     'int',
        #'PositiveIntegerField': 'integer CONSTRAINT [CK_int_pos_%(column)s] CHECK ([%(column)s] >= 0)',
        #'PositiveSmallIntegerField': 'smallint CONSTRAINT [CK_smallint_pos_%(column)s] CHECK ([%(column)s] >= 0)',
        'SlugField':         'nvarchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField':         'nvarchar(max)',
        'TimeField':         'datetime',
    #}
    })

    def _destroy_test_db(self, test_database_name, verbosity):
        "Internal implementation - remove the test db tables."
        cursor = self.connection.cursor()
        self.set_autocommit()
        #time.sleep(1) # To avoid "database is being accessed by other users" errors.
        cursor.execute("ALTER DATABASE %s SET SINGLE_USER WITH ROLLBACK IMMEDIATE " % \
                self.connection.ops.quote_name(test_database_name))
        cursor.execute("DROP DATABASE %s" % \
                self.connection.ops.quote_name(test_database_name))
        self.connection.close()

    def create_test_db(self, verbosity=1, autoclobber=False):
        """
        Duplicate of BaseDatabaseCreation.create_test_db to disable broken Site id coersion.
        Fixes django #17467 that was introduced by django #15573.
        """
        # Don't import django.core.management if it isn't needed.
        from django.core.management import call_command

        test_database_name = self._get_test_db_name()

        if verbosity >= 1:
            test_db_repr = ''
            if verbosity >= 2:
                test_db_repr = " ('%s')" % test_database_name
            print "Creating test database for alias '%s'%s..." % (self.connection.alias, test_db_repr)

        self._create_test_db(verbosity, autoclobber)

        self.connection.close()
        self.connection.settings_dict["NAME"] = test_database_name

        # Confirm the feature set of the test database
        self.connection.features.confirm()

        # Report syncdb messages at one level lower than that requested.
        # This ensures we don't get flooded with messages during testing
        # (unless you really ask to be flooded)
        call_command('syncdb',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias,
            load_initial_data=False)

        # We need to then do a flush to ensure that any data installed by
        # custom SQL has been removed. The only test data should come from
        # test fixtures, or autogenerated from post_syncdb triggers.
        # This has the side effect of loading initial data (which was
        # intentionally skipped in the syncdb).
        call_command('flush',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias)
       
        # One effect of calling syncdb followed by flush is that the id of the
        # default site may or may not be 1, depending on how the sequence was
        # reset.  If the sites app is loaded, then we report a mismatch.
        from django.db.models import get_model
        from django.conf import settings
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            Site = get_model('sites', 'Site')
            if Site is not None and Site.objects.using(self.connection.alias).count() == 1:
                site_id = Site.objects.using(self.connection.alias).all().values_list('id', flat=True)[0]
               
                if site_id != settings.SITE_ID:
                     print "settings.SITE_ID does not match Site object. This may cause some tests to fail."

        from django.core.cache import get_cache
        from django.core.cache.backends.db import BaseDatabaseCache
        for cache_alias in settings.CACHES:
            cache = get_cache(cache_alias)
            if isinstance(cache, BaseDatabaseCache):
                from django.db import router
                if router.allow_syncdb(self.connection.alias, cache.cache_model_class):
                    call_command('createcachetable', cache._table, database=self.connection.alias)

        # Get a cursor (even though we don't need one yet). This has
        # the side effect of initializing the test database.
        self.connection.cursor()

        return test_database_name
