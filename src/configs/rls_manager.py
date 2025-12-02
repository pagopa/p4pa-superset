import logging
from superset.security import SupersetSecurityManager
from configs.dto.pu_user_info_dto import PUUserInfo
from configs.utils.db_utils import SupersetDatabaseUtils
from configs.utils.configuration_utils import ConfigurationUtils
from configs.utils.constant_utils import ConstantUtils
from configs.utils.superset_resource_utils import SupersetResourceUtils
from configs.connector.debt_position_connector import DebtPositionConnector
from configs.rls_builder.rls_builders import RlsBuilderUtils

DEBT_POSITIONS_TYPE_ORG_URL = ConstantUtils.getDebtPositionsTypeOrgURL()

ANALYTICS_DB_NAME = ConstantUtils.getAnalyticsDbName()
ANALYTICS_DB_SCHEMA_NAME = ConstantUtils.getAnalyticsDbSchemaName()

logger = logging.getLogger(__name__)

class RlsManager:
    def upsert_all_rls(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo, http_headers: dict):
        for rls_builder in RlsBuilderUtils.getRlsBuilderList():
            self.__upsert_rls(
                sm, pu_user_info,
                rls_builder.build_rls_name(pu_user_info.id),
                rls_builder.build_rls_group(), # RLS with the same group key will be ORed together, while different RLS groups will be ANDed together. Undefined group keys are treated as unique groups
                rls_builder.build_rls_clause(pu_user_info, http_headers),
                rls_builder.get_apply_to_datasource_list()
            )

    def __upsert_rls(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo,
                     rls_name, rls_group, rls_clause, datasource_name_list: list):
        logger.info(f'Fetching RLS {rls_name}')
        rls = SupersetDatabaseUtils.fetch_row_level_security(rls_name)
        if rls:
            self.__update_rls(sm, rls.id, rls_clause, rls_name, pu_user_info.id, datasource_name_list)
            return
        self.__create_regular_rls(sm, rls_group, rls_clause, rls_name, pu_user_info.id, datasource_name_list)

    def __update_rls(self, sm: SupersetSecurityManager, rls_id, rls_clause, rls_name, user_identifier, datasource_name_list):
        from superset.commands.security.update import UpdateRLSRuleCommand

        logger.info(f'Updating already existing RLS {rls_name}')
        updated_rls = {
            "clause": rls_clause,
            "roles": [
                sm.find_role(ConstantUtils.getSupersetRolePrefix() + user_identifier).id
            ],
            "tables": SupersetDatabaseUtils.fetch_all_datasource_id_in_list(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name_list)
        }
        try:
            UpdateRLSRuleCommand(rls_id, updated_rls).run()
        except Exception as ex:
            logger.error(f"Error updating RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.info(f'Updated RLS {rls_name}')

    def __create_regular_rls(self, sm: SupersetSecurityManager, rls_group, rls_clause, rls_name, user_identifier, datasource_name_list):
        from superset.commands.security.create import CreateRLSRuleCommand

        logger.info(f'Creating RLS {rls_name}')
        rls = {
            "name": rls_name,
            "filter_type": "Regular",
            "clause": rls_clause,
            "group_key": rls_group,
            "roles": [
                sm.find_role(ConstantUtils.getSupersetRolePrefix() + user_identifier).id
            ],
            "tables": SupersetDatabaseUtils.fetch_all_datasource_id_in_list(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name_list)
        }
        try:
            CreateRLSRuleCommand(rls).run()
        except Exception as ex:
            logger.error(f"Error creating RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.info(f'Created RLS {rls_name}')