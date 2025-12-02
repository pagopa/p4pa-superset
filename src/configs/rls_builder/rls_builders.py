from configs.dto.pu_user_info_dto import PUUserInfo
from configs.utils.configuration_utils import ConfigurationUtils
from configs.utils.constant_utils import ConstantUtils
from configs.utils.superset_resource_utils import SupersetResourceUtils
from configs.connector.debt_position_connector import DebtPositionConnector

class RlsBuilderInterface:

    def get_apply_to_datasource_list(self) -> list:
        """Get list of tables to which apply this RLS filter"""
        pass

    def build_rls_name(self, user_identifier: str):
        """Build filter name for this RLS filter"""
        pass

    def build_rls_group(self):
        """Build filter group for this RLS filter"""
        pass

    def build_rls_clause(self, pu_user_info: PUUserInfo, http_headers: dict) -> str:
        """Build filter clause for this RLS filter"""
        pass

class OrgIdAndDebtPositionTypeOrgIdRlsBuilder(RlsBuilderInterface):
    def get_apply_to_datasource_list(self) -> list:
        return ConfigurationUtils.getOrgIdAndDebtPositionTypeOrgIdRLSApplyToDatasourceList()

    def build_rls_name(self, user_identifier: str):
        return ConstantUtils.getSupersetRLSPrefix() + "orgIdAndDPTypeOrg_" + user_identifier

    def build_rls_group(self):
        return "orgIdAndDPTypeOrg"

    def build_rls_clause(self, pu_user_info: PUUserInfo, http_headers: dict):
        return "1=1"

class AlwaysTrueRlsBuilder(RlsBuilderInterface):
    def get_apply_to_datasource_list(self) -> list:
        return ConfigurationUtils.getOrgIdAndDebtPositionTypeOrgIdRLSApplyToDatasourceList()

    def build_rls_name(self, user_identifier: str):
        return ConstantUtils.getSupersetRLSPrefix() + "always_true_" + user_identifier

    def build_rls_group(self):
        return "orgIdAndDPTypeOrg"

    def build_rls_clause(self, pu_user_info: PUUserInfo, http_headers: dict):
        debt_position_type_org_ids = DebtPositionConnector.fetch_dept_position_type_org_ids(
            pu_user_info.id, pu_user_info.organization_id, http_headers
        )
        return SupersetResourceUtils.build_rls_for_org_id_and_debt_position_type_org_id(
            pu_user_info.organization_id, debt_position_type_org_ids
        )

class RlsBuilderUtils:
    __RLS_BUILDER_LIST: list[RlsBuilderInterface] = [
        OrgIdAndDebtPositionTypeOrgIdRlsBuilder(),
        AlwaysTrueRlsBuilder()
    ]

    @staticmethod
    def getRlsBuilderList() -> list[RlsBuilderInterface]:
        return RlsBuilderUtils.__RLS_BUILDER_LIST