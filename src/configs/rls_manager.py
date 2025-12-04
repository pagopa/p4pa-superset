import logging
from superset.security import SupersetSecurityManager
from configs.dto.pu_user_info_dto import PUUserInfo
from configs.utils.db_utils import SupersetDatabaseUtils
from configs.utils.constant_utils import ConnectorConstants, DBConstants, SupersetResourcePrefixConstants
from configs.utils.superset_resource_utils import SupersetResourceUtils
from configs.connector.debt_position_connector import DebtPositionConnector
from configs.rls_builder.rls_builders import RlsBuilderUtils

DEBT_POSITIONS_TYPE_ORG_URL = ConnectorConstants.getDebtPositionsTypeOrgURL()

ANALYTICS_DB_NAME = DBConstants.getAnalyticsDbName()
ANALYTICS_DB_SCHEMA_NAME = DBConstants.getAnalyticsDbSchemaName()

logger = logging.getLogger(__name__)

class RlsManager:
    def upsert_all_rls(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo, http_headers: dict):
        rls_name_list: list = []
        for rls_builder in RlsBuilderUtils.getRlsBuilderList():
            if rls_builder.has_to_be_applied_to_user(pu_user_info):
                rls_name = rls_builder.build_rls_name(pu_user_info.id)
                rls_name_list.append(rls_name)
                self.__upsert_rls(
                    sm, pu_user_info,
                    rls_name,
                    rls_builder.build_rls_group(),
                    rls_builder.build_rls_clause(pu_user_info, http_headers),
                    rls_builder.get_apply_to_datasource_set(pu_user_info)
                )
            else:
                self.__delete_rls(rls_builder.build_rls_name(pu_user_info.id))
        logger.info(f"Assigned to user {pu_user_info.id} following RLS: {rls_name_list}")

    def __upsert_rls(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo,
                     rls_name, rls_group, rls_clause, datasource_name_set: list):
        logger.debug(f'Fetching RLS {rls_name}')
        rls = SupersetDatabaseUtils.fetch_row_level_security(rls_name)
        if rls:
            self.__update_rls(sm, rls.id, rls_clause, rls_name, pu_user_info.id, datasource_name_set)
            return
        self.__create_regular_rls(sm, rls_group, rls_clause, rls_name, pu_user_info.id, datasource_name_set)

    def __update_rls(self, sm: SupersetSecurityManager, rls_id, rls_clause, rls_name, user_identifier, datasource_name_set):
        from superset.commands.security.update import UpdateRLSRuleCommand

        logger.debug(f'Updating already existing RLS {rls_name}')
        updated_rls = {
            "clause": rls_clause,
            "roles": [
                sm.find_role(SupersetResourcePrefixConstants.getSupersetRolePrefix() + user_identifier).id
            ],
            "tables": SupersetDatabaseUtils.fetch_all_datasource_id_in_set(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name_set)
        }
        try:
            UpdateRLSRuleCommand(rls_id, updated_rls).run()
        except Exception as ex:
            logger.error(f"Error updating RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.debug(f'Updated RLS {rls_name}')

    def __create_regular_rls(self, sm: SupersetSecurityManager, rls_group, rls_clause, rls_name, user_identifier, datasource_name_set):
        from superset.commands.security.create import CreateRLSRuleCommand

        logger.debug(f'Creating RLS {rls_name}')
        rls = {
            "name": rls_name,
            "filter_type": "Regular",
            "clause": rls_clause,
            "group_key": rls_group,
            "roles": [
                sm.find_role(SupersetResourcePrefixConstants.getSupersetRolePrefix() + user_identifier).id
            ],
            "tables": SupersetDatabaseUtils.fetch_all_datasource_id_in_set(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name_set)
        }
        try:
            CreateRLSRuleCommand(rls).run()
        except Exception as ex:
            logger.error(f"Error creating RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.debug(f'Created RLS {rls_name}')

    def __delete_rls(self, rls_name):
        from superset.commands.security.delete import DeleteRLSRuleCommand

        logger.debug(f'Fetching RLS {rls_name}')
        rls = SupersetDatabaseUtils.fetch_row_level_security(rls_name)
        if not rls:
            logger.debug(f'RLS {rls_name} nof found')
            return
        logger.debug(f'Deleting existing RLS {rls_name}')
        try:
            DeleteRLSRuleCommand([rls.id]).run()
        except Exception as ex:
            logger.error(f"Error deleting RLS rule {rls_name}: {str(ex)}")
            raise ex
        logger.debug(f'Deleted RLS {rls_name}')
        return