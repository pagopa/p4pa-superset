class PUUserInfo:
    def __init__(self, id, organization_id: int, organization_code: str, broker_code: str, user_roles: list[str]):
        self.id = id
        self.organization_id = organization_id
        self.organization_code = organization_code
        self.broker_code = broker_code
        self.user_roles = user_roles

    @staticmethod
    def build_pu_user_info(user_data: dict):
        return PUUserInfo(
            id=user_data.get('mappedExternalUserId'),
            organization_id=user_data.get('resource').get('organization').get('organizationId'),
            organization_code=user_data.get('resource').get('organization').get('organizationFiscalCode'),
            broker_code=user_data.get('brokerFiscalCode'),
            user_roles=user_data.get('resource').get('organization').get('roles', [])
        )