import subprocess
import os

from django.db.backends import BaseDatabaseClient


IS_WINDOWS = (os.name == 'nt')


class DatabaseClient(BaseDatabaseClient):

    def get_executable_name(self):
        return 'osql' if IS_WINDOWS else 'isql'

    def runshell(self):
        settings_dict = self.connection.settings_dict
        user = settings_dict['USER']
        password = settings_dict['PASSWORD']

        if IS_WINDOWS:
            db = settings_dict['NAME']
            server = settings_dict['HOST']
            #port = settings_dict['PORT']  # never used?
            defaults_file = settings_dict['OPTIONS'].get('read_default_file')

            args = [self.get_executable_name()]
            if server:
                args += ["-S", server]
            if user:
                args += ["-U", user]
                if password:
                    args += ["-P", password]
            else:
                args += ["-E"]  # Try trusted connection instead
            if db:
                args += ["-d", db]
            if defaults_file:
                args += ["-i", defaults_file]
        else:
            dsn = settings_dict['OPTIONS']['dsn']
            args = ['%s -v %s %s %s' % (self.get_executable_name(),
                dsn, user, password)]

        try:
            subprocess.call(args, shell=True)
        except KeyboardInterrupt:
            pass
