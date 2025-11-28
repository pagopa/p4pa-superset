from superset import db

class SupersetDatabaseUtils:
    @staticmethod
    def fetch_row_level_security(rls_name):
        from superset.connectors.sqla.models import RowLevelSecurityFilter

        return (
            db.session.query(RowLevelSecurityFilter)
            .filter_by(name=rls_name)
            .first()
        )

    @staticmethod
    def fetch_superset_datasource(database_name, schema, datasource_name):
        from superset.models.core import Database
        from superset.connectors.sqla.models import SqlaTable

        database = db.session.query(Database).filter_by(database_name=database_name).first()
        if not database:
            logger.warning(f'Database {database_name} does not exist')
            return None

        datasource = (
            db.session.query(SqlaTable)
            .filter_by(
                table_name=datasource_name,
                schema=schema,
                database_id=database.id
            ).first()
        )
        if not datasource:
            logger.warning(f'Datasource {datasource_name} does not exist in schema {schema} of database {database_name}')
            return None
        return datasource