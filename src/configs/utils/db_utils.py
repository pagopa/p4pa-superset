from superset import db
import logging

logger = logging.getLogger(__name__)

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

    @staticmethod
    def fetch_all_datasource_id_in_list(analytics_db_name, analytics_db_schema_name, datasource_name_list):
        datasource_list = [
            SupersetDatabaseUtils.fetch_superset_datasource(analytics_db_name, analytics_db_schema_name, datasource_name)
            for datasource_name in datasource_name_list
        ]
        return [datasource.id for datasource in datasource_list if datasource is not None]