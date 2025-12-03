from enum import Enum
from configs.utils.constant_utils import SupersetRoleNameConstants, PURoleNameConstants
from configs.dto.pu_user_info_dto import PUUserInfo

class SupersetRole(str, Enum):
    DEFAULT = SupersetRoleNameConstants.getSupersetDefaultRoleName()
    OPERATOR = SupersetRoleNameConstants.getSupersetOperatorRoleName()
    ORGANIZATION_ADMIN = SupersetRoleNameConstants.getSupersetOrganizationAdminRoleName()
    BROKER_ADMIN = SupersetRoleNameConstants.getSupersetBrokerAdminRoleName()

class SupersetRoleUtils:
    __superset_roles: set[str] = {
        SupersetRole.DEFAULT,
        SupersetRole.OPERATOR,
        SupersetRole.ORGANIZATION_ADMIN,
        SupersetRole.BROKER_ADMIN
    }

    @staticmethod
    def getSupersetRoleSet() -> set[str]:
        return SupersetRoleUtils.__superset_roles

    @staticmethod
    def get_user_role(pu_user_info) -> str:
        if SupersetRoleUtils.__is_operator(pu_user_info):
            return SupersetRole.OPERATOR
        elif SupersetRoleUtils.__is_organization_admin(pu_user_info):
            return SupersetRole.ORGANIZATION_ADMIN
        elif SupersetRoleUtils.__is_broker_admin(pu_user_info):
            return SupersetRole.BROKER_ADMIN
        else:
            return SupersetRole.DEFAULT

    @staticmethod
    def __is_operator(pu_user_info: PUUserInfo):
        if (PURoleNameConstants.getPUOperatorRoleName() in pu_user_info.user_roles
                and PURoleNameConstants.getPUAdminRoleName() not in pu_user_info.user_roles):
            return True
        else:
            return False

    @staticmethod
    def __is_organization_admin(pu_user_info: PUUserInfo):
        if (PURoleNameConstants.getPUAdminRoleName() in pu_user_info.user_roles
                and pu_user_info.organization_code != pu_user_info.broker_code):
            return True
        else:
            return False

    @staticmethod
    def __is_broker_admin(pu_user_info: PUUserInfo):
        if (PURoleNameConstants.getPUAdminRoleName() in pu_user_info.user_roles
                and pu_user_info.organization_code == pu_user_info.broker_code):
            return True
        else:
            return False
