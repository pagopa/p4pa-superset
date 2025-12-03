from configs.dto.pu_user_info_dto import PUUserInfo
from configs.utils.db_utils import DatasourceEnum
from configs.utils.permission_utils import PermissionUtils
from configs.utils.constant_utils import SupersetResourcePrefixConstants
from configs.utils.superset_resource_utils import SupersetResourceUtils
from configs.connector.debt_position_connector import DebtPositionConnector

class RlsBuilderInterface:
    def has_to_be_applied_to_user(self, pu_user_info: PUUserInfo) -> bool:
        """If this RLS filter should be applied to logging user"""
        if len(self.get_apply_to_datasource_set(pu_user_info)) > 0:
            return True
        else:
            return False

    def get_apply_to_datasource_set(self, pu_user_info: PUUserInfo) -> set:
        """Get list of datasource to which apply this RLS filter"""
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
    def get_apply_to_datasource_set(self, pu_user_info: PUUserInfo) -> set:
        __org_id_and_dp_type_org_id_rls_apply_to_datasource_set: set[str] = {
            DatasourceEnum.ASSESSMENT_CLASSIFIED
        }
        return (
            __org_id_and_dp_type_org_id_rls_apply_to_datasource_set
            .intersection(PermissionUtils.getUserRoleDatasourcePermissionSet(pu_user_info))
        )

    def build_rls_name(self, user_identifier: str):
        return SupersetResourcePrefixConstants.getSupersetRLSPrefix() + "orgIdAndDPTypeOrg_" + user_identifier

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
    __RLS_BUILDER_SET: set[RlsBuilderInterface] = {
        OrgIdAndDebtPositionTypeOrgIdRlsBuilder()
    }

    @staticmethod
    def getRlsBuilderList() -> set[RlsBuilderInterface]:
        return RlsBuilderUtils.__RLS_BUILDER_SET