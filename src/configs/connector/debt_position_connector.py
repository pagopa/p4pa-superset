import logging
import requests
from configs.utils.constant_utils import ConnectorConstants

logger = logging.getLogger(__name__)

class DebtPositionConnector:

    @staticmethod
    def fetch_dept_position_type_org_ids(user_identifier, organization_id, http_headers: dict):
        logger.info(f'Fetching DebtPositionTypeOrgs for user {user_identifier} and org {organization_id}')
        dp_type_org_data = DebtPositionConnector.__fetch_dept_position_type_orgs(user_identifier, organization_id, http_headers)
        return DebtPositionConnector.__build_debt_position_type_ids_string(dp_type_org_data)

    @staticmethod
    def __fetch_dept_position_type_orgs(user_identifier, organization_id, http_headers: dict):
        query_params_dict = {"operatorExternalUserId": user_identifier, "organizationId": organization_id}
        response = requests.get(
            ConnectorConstants.getDebtPositionsTypeOrgURL(),
            params=query_params_dict,
            headers=http_headers,
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def __build_debt_position_type_ids_string(debt_position_type_org_data: dict):
        dp_type_org_ids_string = ""
        for debt_position_type_org in debt_position_type_org_data.get("_embedded").get("debtPositionTypeOrgs"):
            if len(dp_type_org_ids_string) > 0:
                dp_type_org_ids_string += ","
            dp_type_org_ids_string += "'"
            dp_type_org_ids_string += str(debt_position_type_org.get("debtPositionTypeOrgId"))
            dp_type_org_ids_string += "'"
        return dp_type_org_ids_string