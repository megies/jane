# Production Server Maintenance

In the following it is assumed, that a production server is setup with Apache
and PostgreSQL as described in the previous section. This is mostly a writeup
of actions taken to update the production instance with regard to [an issue
tracked on Github](https://github.com/krischer/jane/issues/84).

### Setting up a Development/Maintenance Server

This section presents a possible approach to make a near identical clone of the
production server (if not already set up), in order to use it for
development/maintenance/updating/testing purposes together with the live
production server.

#### On Production Server

Before cloning most parts of the production server, it is a good idea to get an
idea of how big the individual tables in the database are. For PostgreSQL, we
can do this by executing the following SQL query (e.g. in a `psql` command
shell or via `pgadmin3` GUI):

```bash
jane@jane:~$ psql jane
psql (9.4.15)
Type "help" for help.

jane=> SELECT relname as "Table",
jane-> pg_size_pretty(pg_total_relation_size(relid)) As "Size",
jane-> pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as "External Size"
jane-> FROM pg_catalog.pg_statio_user_tables
jane-> ORDER BY pg_total_relation_size(relid) DESC;
jane=> \q
```

..which might result in something like the following result:

```plain
                    Table                    |  Size   | External Size 
---------------------------------------------+---------+---------------
 waveforms_continuoustrace                   | 127 GB  | 99 GB
 waveforms_file                              | 4885 MB | 4548 MB
 documents_document                          | 94 MB   | 90 MB
 documents_documentindexattachment           | 87 MB   | 87 MB
 documents_documentindex                     | 11 MB   | 3128 kB
 spatial_ref_sys                             | 3360 kB | 176 kB
 waveforms_path                              | 2880 kB | 1776 kB
 django_admin_log                            | 1808 kB | 1008 kB
 waveforms_mapping                           | 208 kB  | 200 kB
 django_session                              | 112 kB  | 88 kB
 documents_documenttype                      | 104 kB  | 96 kB
 djangoplugins_plugin                        | 96 kB   | 88 kB
 auth_permission                             | 96 kB   | 80 kB
 documents_documenttype_validators           | 88 kB   | 80 kB
 documents_documenttype_retrieve_permissions | 88 kB   | 80 kB
 auth_user_user_permissions                  | 72 kB   | 64 kB
 waveforms_restriction                       | 64 kB   | 64 kB
 auth_user                                   | 56 kB   | 48 kB
 documents_documenttype_upload_permissions   | 40 kB   | 40 kB
 django_content_type                         | 40 kB   | 32 kB
 auth_group_permissions                      | 32 kB   | 32 kB
 djangoplugins_pluginpoint                   | 32 kB   | 24 kB
 django_migrations                           | 32 kB   | 24 kB
 auth_user_groups                            | 32 kB   | 32 kB
 waveforms_restriction_users                 | 32 kB   | 32 kB
 auth_group                                  | 24 kB   | 24 kB
(26 rows)
```

So we see that we can easily clone everything but the data content in the two
largest tables. By cloning instead of setting up tables manually, we make sure
that the database state on the development server is exactly the same as with
the production server, which is what we want when creating django migrations
that can be applied on the production server. So first we dump all the smaller
tables (as user `postgres`). For simplicity we will use the same postgres user
and database names on the development server (otherwise additional options like
`--no-user`/`--no-owner` might have to be added and additional steps on the
testing server when setting up the dumped databases will likely be necessary):

```bash
jane@jane:~$ su
Password:
root@jane:~# su postgres
postgres@jane:~$ cd /tmp
postgres@jane:/tmp$ pg_dump jane --exclude-table-data '*.waveforms_continuoustrace' --exclude-table-data '*.waveforms_file' --file jane.sql
```

For the big tables, it would be overkill to clone all data, so instead we
extract a (more or less random) subset of the original data (as user
`postgres`). In this example we select every 500th waveform file entry,
limiting output to a maximum of 10000 entries (actually the output we get are
only 3703 lines anyway).

```plain
postgres@jane:/tmp$ psql jane
psql (9.4.15)
Type "help" for help.

jane=# COPY (
jane(#   SELECT t.*
jane(#   FROM (
jane(#     SELECT *, row_number()
jane(#     OVER(ORDER BY id ASC) AS row
jane(#     FROM waveforms_file) t
jane(#   WHERE t.row % 500 = 0 LIMIT 10000)
jane-# TO '/tmp/jane_waveforms_file.csv'
jane-# CSV HEADER;
COPY 3703
```

Now we also select a subset of the `waveforms_contiguoustrace` table, while
making sure that we select rows that match the previously extracted waveform
files from `waveforms_file` table (it might actually not be necessary for the
maintenance operations we perform later that these entries match, this is just
to be on the safe side).

```sql
jane=# COPY (
jane(#   SELECT *
jane(#   FROM waveforms_continuoustrace
jane(#   WHERE file_id IN (
jane(#     SELECT t.id
jane(#     FROM (
jane(#       SELECT *, row_number()
jane(#       OVER(ORDER BY id ASC) AS row
jane(#       FROM waveforms_file) t
jane(#     WHERE t.row % 500 = 0 LIMIT 10000)
jane(#   LIMIT 50000)
jane-# TO '/tmp/jane_waveforms_ct.csv'
jane-# CSV HEADER;
COPY 50000
jane=# \q
```

The previous command has added an unwanted additional column `row` that we need
to remove from the dumped csv file e.g. using `sed`.

```bash
postgres@jane:/tmp$ cat jane_waveforms_file.csv | sed -e 's#,[^,]*$##' > jane_waveforms_file_clean.csv
```

#### On Development Server

The following will assume, that postgres is running as a database backend in
the same version on the development server (in this case two Debian 8 Jessie
installations). Now on the development/maintenance server, we restore the
dumped database (using same user/table name as on production) as user
"postgres" (copied from production server to development server e.g. via
`scp`). First we need to create the appropriate postgres user (if not yet
present). If an old development database already existed we might have to drop
if first (careful, all data is lost) and create a new empty database into which
we then import the dumped table data.

```bash
tremor@unzen:~$ su
Password:
root@unzen:~# su postgres
postgres@unzen:~$ createuser --encrypted --pwprompt jane
postgres@unzen:~$ #dropdb jane  # careful!
postgres@unzen:~$ createdb -T template0 --owner jane jane
postgres@unzen:~$ psql jane < /tmp/jane.sql
SET
SET
SET
SET
SET
SET
CREATE EXTENSION
COMMENT
CREATE EXTENSION
COMMENT
SET
[...]
ALTER TABLE
ALTER TABLE
ALTER TABLE
REVOKE
REVOKE
GRANT
GRANT
postgres@unzen:~$
```

Now in addition we also have to import those subsample csv files for the
largest tables (again, as user "postgres").

```bash
postgres@unzen:~$ psql jane
jane=# \copy waveforms_file FROM '/tmp/jane_waveforms_file_clean.csv' DELIMITER ',' CSV HEADER
COPY 3703
jane=# \copy waveforms_continuoustrace FROM '/tmp/jane_waveforms_ct.csv' DELIMITER ',' CSV HEADER
COPY 50000
jane=# \q
```

Now what is left is to also setup an identical Python installation on the
development server. In this case the production server is setup as described in
the previous section, i.e. relying on Debian Python packages and some
additional packages installed in user space with `pip install --user` (on
Debian this ends up in `~/.local` by default).

So first of all, install the same Debian Python 3 packages as on the production
server. The manually installed packages can be looked up on the production
server by doing e.g.

```bash
jane@jane:~$ aptitude search python3 | egrep '^i   '
i   python3-all                     - package depending on all supported Python 
i   python3-all-dev                 - package depending on all supported Python 
i   python3-defusedxml              - XML bomb protection for Python stdlib modu
i   python3-doc                     - documentation for the high-level object-or
i   python3-examples                - examples for the Python language (default 
i   python3-flake8                  - code checker using pycodestyle and pyflake
i   python3-gdal                    - Python 3 bindings to the Geospatial Data A
i   python3-geopy                   - geocoding toolbox for Python3             
i   python3-markdown                - text-to-HTML conversion library/tool (impl
i   python3-minimal                 - minimal subset of the Python language (def
i   python3-obspy                   - ObsPy: A Python Toolbox for seismology    
i   python3-pip                     - alternative Python package installer - Pyt
i   python3-psycopg2                - Python 3 module for PostgreSQL            
i   python3-yaml                    - YAML parser and emitter for Python3       
```

After installing these packages on the development server, we can then simply
copy the additionally installed packages, e.g. using rsync or scp. In this
example we deliberately copy the additional packages to a different directory
that will not be picked up by Python by default, in order to not interfere with
other tasks that are running on the development server.

```bash
tremor@unzen:~$ rsync -a jane@jane:.local/ .local-jane-dev  # trailing slash makes a difference!
```

We can later tell python to regard this directory explicitly for an individual
Python prompt / program execution by means of the `PYTHONUSERBASE` environment
variable..

```bash
tremor@unzen:~$ PYTHONUSERBASE=$HOME/.local-jane-dev /usr/bin/python3
```

Now finally, the jane installation (which is assumed to be a local git
repository, connected to a github remote repository) can also be cloned using
`rsync` (addresses of registered remotes might have to be adapted if using
remotes with GPG private/public key authentication).

```bash
tremor@unzen:~$ rsync -av jane@jane:jane/ jane-dev  # trailing slash makes a difference!
```

Now some settings have to be adjusted in the local settings on the development
server (most likely only database connection as shown here), so edit key
`DATABASES` in file `~/jane-dev/src/jane/local_settings.py` on development
server (e.g. adjust password if using something else than on production
server).

We can then run the Jane development instance on the development server
(without Apache backend) and allowing connections from all other machines in
the network:

```bash
tremor@unzen:~$ cd ~/jane-dev/src
tremor@unzen:~/jane-dev/src$ PYTHONUSERBASE=$HOME/.local-jane-dev /usr/bin/python3 manage.py runserver 0.0.0.0:8000
```

The development Jane instance can be then accessed from workstations at web
address `http://unzen:8000`.


### Updating Jane / Doing Migrations

In the following it is summarized how to perform updates on the Jane production
instance, especially when database changes are involved which is handled by so
called django "migrations". In general, these migrations are created and
applied on the development server (which therefore obviously should be in the
same state with regard to database schema/layout), committed to version control
and then applied on the production server.

#### On Development Server

 - stop jane (usually is not running anyway, as it is not served via apache)
 - make sure all current migrations are applied

        tremor@unzen:~/jane-dev/src$ export PYTHONUSERBASE=$HOME/.local-jane-dev
        tremor@unzen:~/jane-dev/src$ /usr/bin/python3 manage.py migrate
        Operations to perform:
          Apply all migrations: documents, admin, waveforms, contenttypes, sessions, djangoplugins, auth
        Running migrations:
          No migrations to apply.

 - `git pull` in new changes from github and/or make local changes and commit
   them, see e.g.
   [here](https://github.com/krischer/jane/commit/fccfcaf8f92bb86f5baa630153a5b0824cdd1e6f)
   for a commit that affects the database schema and that needs a migration
 - take notes what should change after a successful update
    - feature changes in the web pages, GIS etc.
    - changes to database layout
    - ...

 - when on a clean commit state of the deployed git branch, have django set up
   migrations and optionally rename them to have a meaningful name (only ever
   rename not-yet-applied migrations!!), see e.g.
   [here](https://github.com/krischer/jane/commit/956cf03a90a993a6b872e8c3e412acdd268df482)
   for a commit with a migration created in this way

        tremor@unzen:~/jane-dev/src$ /usr/bin/python3 manage.py makemigrations
        Migrations for 'waveforms':
          0003_auto_20180821_1331.py:
            - Alter unique_together for continuoustrace (1 constraint(s))
        tremor@unzen:~/jane-dev/src$ mv jane/waveforms/migrations/0003_auto_{20180821_1331,waveform_continuoustrace_unique_constraint}.py

 - apply new migration (check what django wants to do beforehand)

        tremor@unzen:~/jane-dev/src$ /usr/bin/python3 manage.py showmigrations
        admin
         [X] 0001_initial
         [X] 0002_logentry_remove_auto_add
        auth
         [X] 0001_initial
         [X] 0002_alter_permission_name_max_length
         [X] 0003_alter_user_email_max_length
         [X] 0004_alter_user_username_opts
         [X] 0005_alter_user_last_login_null
         [X] 0006_require_contenttypes_0002
         [X] 0007_alter_validators_add_error_messages
        contenttypes
         [X] 0001_initial
         [X] 0002_remove_content_type_name
        djangoplugins
         [X] 0001_initial
        documents
         [X] 0001_initial
         [X] 0002_auto_20161018_0646
        sessions
         [X] 0001_initial
        waveforms
         [X] 0001_initial
         [X] 0002_auto_20160706_1508
         [ ] 0003_auto_waveform_continuoustrace_unique_constraint
        tremor@unzen:~/jane-dev/src$ /usr/bin/python3 manage.py migrate
        Operations to perform:
          Apply all migrations: documents, sessions, waveforms, contenttypes, admin, djangoplugins, auth
        Running migrations:
          Rendering model states... DONE
          Applying waveforms.0003_auto_waveform_continuoustrace_unique_constraint... OK

 - if any index fields in the indexed json document data has changed, kick of a
   reindexing of the related document type! (currently there is no means to
   request a reindexing of existing documents, so one has to download all
   documents, delete them on server and upload them again..)
 - check that all changes were performed successfully
    - check database model/table changes (e.g. new columns, changed unique
      constraints, ...)
    - after running the development server check that any web page/GIS feature
      changes are reflected correctly
 - commit new migration to git repository and push to github

#### On Production Server

 - stop any processes acting on the postgres databases
    - stop jane (i.e. stop apache in our case)
    - stop indexers (e.g. `pkill --signal 1 -f 'manage.py index_waveforms '`)
    - check that postgres is indeed idle and there are no long running active queries,
      e.g. doing a SQL query:

            postgres@unzen:~$ psql
            psql (9.4.15)
            Type "help" for help.
            
            postgres=# SELECT * FROM pg_stat_activity;
            postgres=# SELECT pid, now() - a.query_start AS duration, query, state
            postgres-# FROM pg_stat_activity AS a
            postgres-# WHERE state = 'active';
              pid  | duration |                            query                            | state  
            -------+----------+-------------------------------------------------------------+--------
             12535 | 00:00:00 | SELECT pid, now() - a.query_start AS duration, query, state+| active
                   |          | FROM pg_stat_activity AS a                                 +| 
                   |          | WHERE state = 'active';                                     | 
            (1 row)
            
            postgres=# \q

    - if necessary, kill long running queries that would hold up the update
      (obviously only if those are queries that only read the database, not add new
      information!):

            postgres=# SELECT pg_cancel_backend(<PID of query, see above request that lists active queries>)

 - ideally make backup of database, or at least of the parts that would would
   hurt if lost, or at least check that scheduled backups are done regularly
 - make sure all current migrations are applied

        jane@jane:~/jane/src$ /usr/bin/python3 manage.py migrate

 - `git pull` latest changes on deployed branch (created and pushed above on
   development server)
 - apply new migration, if any

        jane@jane:~/jane/src$ /usr/bin/python3 manage.py migrate

 - if static page contents have changed, update exported static pages

        jane@jane:~/jane/src$ /usr/bin/python3 manage.py collectstatic

 - start jane (i.e. start apache in our case)
 - start waveform indexers, if necessary
 - check if everything works as expected
 - party!
