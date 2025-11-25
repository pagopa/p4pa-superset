import logging
import os
from superset import db
import requests

DEBT_POSITIONS_TYPE_ORG_URL = os.environ.get('DEBT_POSITIONS_BASE_URL') + "/crud/debt-position-type-orgs/search/findDebtPositionTypeOrgs"
ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
SCHEMA_AND_TABLE_NAME_LIST_STRING = os.environ.get("SCHEMA_AND_TABLE_NAME_LIST_STRING")
logger = logging.getLogger(__name__)

class RlsManager:

    def upsert_rls(self, user_identifier, organization_id, http_headers: dict):
        self.__upsert_org_id_and_dp_type_org_ids_rls(
            user_identifier,
            organization_id,
            http_headers,
            SCHEMA_AND_TABLE_NAME_LIST_STRING.split(",")
        )

    def __upsert_org_id_and_dp_type_org_ids_rls(self, user_identifier, organization_id,
                                              http_headers: dict, schema_and_table_name_list: list):
        from superset.connectors.sqla.models import RowLevelSecurityFilter

        logger.info('Executing method upsert_rls')
        rls_name = "rls_" + user_identifier
        rls_group = "dpTypeOrg"
        logger.info('Building RLS clause')
        rls_clause = self.__build_org_id_and_dp_type_orgs_id_rls_clause(user_identifier, organization_id, http_headers)

        logger.info('Try fetching RLS')
        rls = (
            db.session.query(RowLevelSecurityFilter)
            .filter_by(name=rls_name)
            .first()
        )
        if rls:
            self.__update_rls(rls, rls_clause, rls_name)
            return

        self.__create_regular_rls(rls_clause, rls_group, rls_name, user_identifier, schema_and_table_name_list)

    def __build_org_id_and_dp_type_orgs_id_rls_clause(self, user_identifier, organization_id, http_headers: dict):
        logger.info(f'Fetching DebtPositionTypeOrgs for user {user_identifier} and org {organization_id}')
        debt_position_type_org_data = self.__fetch_dept_position_type_orgs(user_identifier, organization_id, http_headers)
        debt_position_type_org_ids_string = self.__build_debt_position_type_ids_string(debt_position_type_org_data)
        return f"organization_id = '{organization_id}' and debt_position_type_org_id in ({debt_position_type_org_ids_string})"

    def __fetch_dept_position_type_orgs(self, user_identifier, organization_id, http_headers: dict):
        query_params_dict = {"operatorExternalUserId": user_identifier, "organizationId": organization_id}
        response = requests.get(
            DEBT_POSITIONS_TYPE_ORG_URL,
            params=query_params_dict,
            headers=http_headers,
            timeout=5,
            verify=False
        )
        response.raise_for_status()
        return response.json()

    def __build_debt_position_type_ids_string(self, debt_position_type_org_data: dict):
        dp_type_org_ids_string = ""
        for debt_position_type_org in debt_position_type_org_data.get("_embedded").get("debtPositionTypeOrgs"):
            if len(dp_type_org_ids_string) > 0:
                dp_type_org_ids_string += ","
            dp_type_org_ids_string += "'"
            dp_type_org_ids_string += str(debt_position_type_org.get("debtPositionTypeOrgId"))
            dp_type_org_ids_string += "'"
        return dp_type_org_ids_string

    def __update_rls(self, rls, rls_clause, rls_name):
        logger.info(f'Updating already existing RLS {rls_name}')
        rls.clause = rls_clause
        rls.table = self.__fetch_all_database_tables_in_list(
            database_name=ANALYTICS_DB_NAME,
            schema_and_table_name_list=SCHEMA_AND_TABLE_NAME_LIST_STRING.split(",")
        )
        db.session.commit()
        logger.info(f'Updated RLS {rls_name}')

    def __create_regular_rls(self, rls_clause, rls_group, rls_name, user_identifier, schema_and_table_name_list):
        from superset.connectors.sqla.models import RowLevelSecurityFilter
        from flask_appbuilder.security.sqla.models import Role

        logger.info(f'Creating RLS {rls_name}')
        rls = RowLevelSecurityFilter(
            name=rls_name,
            filter_type="Regular",
            clause=rls_clause,
            group_key=rls_group,
            roles=[db.session.query(Role).filter_by(name=f"role_{user_identifier}").first()],
            tables=self.__fetch_all_database_tables_in_list(
                database_name=ANALYTICS_DB_NAME,
                schema_and_table_name_list=schema_and_table_name_list
            )
        )
        db.session.add(rls)
        db.session.commit()
        logger.info(f'Created RLS {rls_name}')

    def __fetch_all_database_tables_in_list(self, database_name, schema_and_table_name_list):
        schema_and_table_name_tuple_list = [
            (schema_and_table.split('|')[0], schema_and_table.split('|')[1])
            for schema_and_table in schema_and_table_name_list
        ]
        db_tables = [
            self.__fetch_single_database_table(database_name, schema_and_table_tuple[0], schema_and_table_tuple[1])
            for schema_and_table_tuple in schema_and_table_name_tuple_list
        ]
        return [table for table in db_tables if table is not None]

    def __fetch_single_database_table(self, database_name, schema, table_name):
        from superset.models.core import Database
        from superset.connectors.sqla.models import SqlaTable

        database = db.session.query(Database).filter_by(database_name=database_name).first()
        if not database:
            logger.warning(f'Database {database_name} does not exist')
            return None

        table = (
            db.session.query(SqlaTable)
            .filter_by(
                table_name=table_name,
                schema=schema,
                database_id=database.id
            ).first()
        )
        if not table:
            logger.warning(f'Table {table_name} does not exist in schema {schema} of database {database_name}')
            return None
        return table