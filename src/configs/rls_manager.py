import logging
import os
from superset.security import SupersetSecurityManager
import requests
from pu_user_info_dto import PUUserInfo
from db_utils import SupersetDatabaseUtils
from configuration_utils import ConfigurationUtils

DEBT_POSITIONS_TYPE_ORG_URL = os.environ.get('DEBT_POSITIONS_BASE_URL') + "/crud/debt-position-type-orgs/search/findDebtPositionTypeOrgs"

ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
ANALYTICS_DB_SCHEMA_NAME = os.environ.get('ANALYTICS_DB_SCHEMA_NAME')

logger = logging.getLogger(__name__)

class RlsManager:

    def upsert_rls(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo, http_headers: dict):
        self.__upsert_org_id_and_dp_type_org_ids_rls(
            sm,
            pu_user_info.id,
            pu_user_info.organization_id,
            http_headers,
            ConfigurationUtils.getAllDatasourceNameList()
        )

    def __upsert_org_id_and_dp_type_org_ids_rls(self, sm: SupersetSecurityManager, user_identifier, organization_id,
                                                http_headers: dict, datasource_name_list: list):

        logger.info('Executing method upsert_rls')
        rls_name = "rls_" + user_identifier
        rls_group = "dpTypeOrg"
        logger.info('Building RLS clause')
        rls_clause = self.__build_org_id_and_dp_type_orgs_id_rls_clause(user_identifier, organization_id, http_headers)

        logger.info('Try fetching RLS')
        rls = SupersetDatabaseUtils.fetch_row_level_security(rls_name)
        if rls:
            self.__update_rls(sm, rls.id, rls_clause, rls_name, user_identifier, datasource_name_list)
            return

        self.__create_regular_rls(sm, rls_clause, rls_group, rls_name, user_identifier, datasource_name_list)

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
            timeout=5
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

    def __update_rls(self, sm: SupersetSecurityManager, rls_id, rls_clause, rls_name, user_identifier, datasource_name_list):
        from superset.commands.security.update import UpdateRLSRuleCommand

        logger.info(f'Updating already existing RLS {rls_name}')
        updated_rls = {
            "clause": rls_clause,
            "roles": [
                sm.find_role(f"role_{user_identifier}").id
            ],
            "tables": self.__fetch_all_datasource_id_in_list(datasource_name_list)
        }
        try:
            UpdateRLSRuleCommand(rls_id, updated_rls).run()
        except Exception as ex:
            logger.error(f"Error updating RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.info(f'Updated RLS {rls_name}')

    def __create_regular_rls(self, sm: SupersetSecurityManager, rls_clause, rls_group, rls_name, user_identifier, datasource_name_list):
        from superset.commands.security.create import CreateRLSRuleCommand

        logger.info(f'Creating RLS {rls_name}')
        rls = {
            "name": rls_name,
            "filter_type": "Regular",
            "clause": rls_clause,
            "group_key": rls_group,
            "roles": [
                sm.find_role(f"role_{user_identifier}").id
            ],
            "tables": self.__fetch_all_datasource_id_in_list(datasource_name_list)
        }
        try:
            CreateRLSRuleCommand(rls).run()
        except Exception as ex:
            logger.error(f"Error creating RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.info(f'Created RLS {rls_name}')

    def __fetch_all_datasource_id_in_list(self, datasource_name_list):
        datasource_list = [
            SupersetDatabaseUtils.fetch_superset_datasource(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name)
            for datasource_name in datasource_name_list
        ]
        return [datasource.id for datasource in datasource_list if datasource is not None]