from configs.utils.constant_utils import ConstantUtils
from configs.dto.pu_user_info_dto import PUUserInfo

class PURoleUtils:
    @staticmethod
    def is_operator(pu_user_info: PUUserInfo):
        if (ConstantUtils.getPUOperatorRoleName() in pu_user_info.user_roles
                and ConstantUtils.getPUAdminRoleName() not in pu_user_info.user_roles):
            return True
        else:
            return False

    @staticmethod
    def is_organization_admin(pu_user_info: PUUserInfo):
        if (ConstantUtils.getPUAdminRoleName() in pu_user_info.user_roles
                and pu_user_info.organization_code != pu_user_info.broker_code):
            return True
        else:
            return False

    @staticmethod
    def is_broker_admin(pu_user_info: PUUserInfo):
        if (ConstantUtils.getPUAdminRoleName() in pu_user_info.user_roles
                and pu_user_info.organization_code == pu_user_info.broker_code):
            return True
        else:
            return False
