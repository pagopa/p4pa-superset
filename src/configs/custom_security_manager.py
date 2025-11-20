import logging
import os
import jwt
from jwt import DecodeError
from superset import db
from superset.security import SupersetSecurityManager
from flask import flash
import requests
from flask_appbuilder.security.views import UserDBModelView,AuthDBView
from flask_appbuilder.security.views import expose
from flask_appbuilder.security.manager import BaseSecurityManager
from flask_login import login_user, logout_user
from flask import g, request, redirect

DEBT_POSITIONS_TYPE_ORG_URL = os.environ.get('DEBT_POSITIONS_BASE_URL') + "/crud/debt-position-type-orgs/search/findDebtPositionTypeOrgs"
USERINFO_URL = os.environ.get('AUTH_BASE_URL') + "/oauth/userinfo"
logger = logging.getLogger(__name__)
class CustomAuthView(AuthDBView):
  login_template = 'appbuilder/general/security/login_db.html'

  @expose('/sso-login/', methods=['GET','POST'])
  def login(self):
    jwt_token = request.args.get('token')
    if not jwt_token:
      return super(CustomAuthView,self).login()
    try:
        decoded_token = jwt.decode(
                    jwt_token,
                    key=None,
                    algorithms=["RS512", "RS256"],
                    options={'verify_signature': False}
                )
        scope = decoded_token.get('scope')
        if scope != 'superset':
                    logger.debug('JWT Scope mismatch: expected "superset", got "%s"', scope)
                    flash("Access SSO denied: scope not authorized.", "danger")
                    return super(CustomAuthView, self).login()
    except DecodeError as e:
            logger.debug('Invalid JWT format: %s', e)
            flash("Format Token Error", "danger")
            return super(CustomAuthView, self).login()
    except Exception as e:
            logger.debug('Generic error during local JWT check: %s', e)
            flash("Error while verify token.", "danger")
            return super(CustomAuthView, self).login()

    if jwt_token:
            try:
                headers = {'Authorization': f'Bearer {jwt_token}'}
                response = requests.get(USERINFO_URL, headers=headers, timeout=5, verify=False)
                response.raise_for_status()
                user_data = response.json()
                user_identifier = user_data.get('mappedExternalUserId')
                organization_id = user_data.get('organizzations', [{}])[0].get('organizationId')
                if user_identifier:
                    sm = self.appbuilder.sm
                    user = sm.find_user(username=user_identifier)
                    if not user and sm.auth_user_registration:
                        first_name = user_data.get('name')
                        last_name =  user_data.get('familyName')
                        email = ''
                        role = sm.find_role(sm.auth_user_registration_role)
                        user = sm.add_user(user_identifier, first_name, last_name, email, role)
                        self.upsert_rls(user_identifier, organization_id, headers)
                    if user:
                        login_user(user, remember=False)
                        self.upsert_rls(user_identifier, organization_id, headers)
                        return redirect(self.appbuilder.get_url_for_index)
                    else:
                         logger.debug('User not found new registration not allowed.')
            except Exception as e:
                logger.debug('Generic error: %s',e)
                return super(CustomAuthView,self).login()
    else:
      logger.debug('Unable to auto login')
      return super(CustomAuthView,self).login()

  def upsert_rls(self: SupersetSecurityManager, user_identifier, organization_id, headers: dict):
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    rls_name= "rls_" + user_identifier
    rls_clause = self.build_rls_clause(user_identifier, organization_id, headers)

    rls = (
        db.session.query(RowLevelSecurityFilter)
        .filter_by(name=rls_name)
        .first()
    )
    if rls:
        logger.info(f'RLS {rls_name} already exists')
        rls.clause = rls_clause
        #rls.table = []
        db.session.commit()
        logger.info(f'RLS {rls_name} updated')
        return

    rls = RowLevelSecurityFilter(
        name = rls_name,
        filter_type = "Regular",
        clause = rls_clause,
        group_key = "dpTypeOrg",
        roles = [],
        tables = []
    )
    db.session.add(rls)
    db.session.commit()

  def build_rls_clause(self, user_identifier, organization_id, headers: dict):
      debt_position_type_org_data = self.fetch_dept_position_type_orgs(organization_id, user_identifier, headers)
      debt_position_type_org_ids_string = self.build_debt_position_type_ids_string(debt_position_type_org_data)
      return f"org_id = '{organization_id}' and dp_type_org_id in ({debt_position_type_org_ids_string})"

  def fetch_dept_position_type_orgs(self, user_identifier, organization_id, headers: dict):
    queryParamsDict = {"operatorExternalUserId": user_identifier, "organizationId": organization_id}
    response = requests.get(DEBT_POSITIONS_TYPE_ORG_URL, params=queryParamsDict, headers=headers, timeout=5, verify=False)
    response.raise_for_status()
    return response.json()

  def build_debt_position_type_ids_string(self, debt_position_type_org_data: dict):
    dp_type_org_ids_string = ""
    for debt_position_type_org in debt_position_type_org_data.get("_embedded").get("debtPositionTypeOrgs"):
        if len(dp_type_org_ids_string) > 0:
            dp_type_org_ids_string += ","
        dp_type_org_ids_string += "'"
        dp_type_org_ids_string += debt_position_type_org.get("debtPositionTypeOrgId")
        dp_type_org_ids_string += "'"
    return dp_type_org_ids_string

class CustomSecurityManager(SupersetSecurityManager):
    authdbview = CustomAuthView
    def __init__(self, appbuilder):
        super(CustomSecurityManager, self).__init__(appbuilder)