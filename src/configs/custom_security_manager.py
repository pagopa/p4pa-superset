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
ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
SCHEMA_AND_TABLE_NAME_LIST_STRING = os.environ.get("SCHEMA_AND_TABLE_NAME_LIST_STRING")
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
                organization_id = user_data.get('resource').get('organization').get('organizationId')
                if user_identifier:
                    sm = self.appbuilder.sm
                    user = sm.find_user(username=user_identifier)
                    if not user and sm.auth_user_registration:
                        first_name = user_data.get('name')
                        last_name =  user_data.get('familyName')
                        email = ''
                        role = sm.find_role(sm.auth_user_registration_role)
                        user = sm.add_user(user_identifier, first_name, last_name, email, role)
                    if user:
                        role = self.create_role_if_missing(f"role_{user_identifier}")
                        self.assign_role_to_user(role, user)
                        role = self.create_role_if_missing("access_to_dp_type_orgs")
                        self.assign_role_to_user(role, user)
                        self.upsert_rls(user_identifier, organization_id, headers)
                        login_user(user, remember=False)
                        return redirect(self.appbuilder.get_url_for_index)
                    else:
                         logger.debug('User not found new registration not allowed.')
            except Exception as e:
                logger.debug('Generic error: %s',e)
                return super(CustomAuthView,self).login()
    else:
      logger.debug('Unable to auto login')
      return super(CustomAuthView,self).login()

  def create_role_if_missing(self, role_name):
    from flask_appbuilder.security.sqla.models import Role

    role = db.session.query(Role).filter_by(name=role_name).first()
    if role:
      return role

    logger.info(f'Creating Role {role_name}')
    role = Role(name=role_name)
    db.session.add(role)
    db.session.commit()

    return role

  def assign_role_to_user(self, role, user):
    if role not in user.roles:
      logger.info(f'Assigning role {role} to user {user.username}')
      user.roles.append(role)
      db.session.commit()

  def upsert_rls(self: SupersetSecurityManager, user_identifier, organization_id, headers: dict):
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    from flask_appbuilder.security.sqla.models import Role

    logger.info('Executing method upsert_rls')
    rls_name= "rls_" + user_identifier
    rls_group="dpTypeOrg"
    logger.info('Building RLS clause')
    rls_clause = self.build_dept_position_type_orgs_rls_clause(user_identifier, organization_id, headers)

    logger.info('Try fetching RLS')
    rls = (
        db.session.query(RowLevelSecurityFilter)
        .filter_by(name=rls_name)
        .first()
    )
    if rls:
        logger.info(f'Updating already existing RLS {rls_name}')
        rls.clause = rls_clause
        rls.table = self.fetch_all_database_tables_in_list(database_name=ANALYTICS_DB_NAME, schema_and_table_name_list=SCHEMA_AND_TABLE_NAME_LIST_STRING.split(","))
        db.session.commit()
        logger.info(f'Updated RLS {rls_name}')
        return

    logger.info(f'Creating RLS {rls_name}')
    rls = RowLevelSecurityFilter(
        name = rls_name,
        filter_type = "Regular",
        clause = rls_clause,
        group_key = rls_group,
        roles = [db.session.query(Role).filter_by(name=f"role_{user_identifier}").first()],
        tables = self.fetch_all_database_tables_in_list(database_name=ANALYTICS_DB_NAME, schema_and_table_name_list=SCHEMA_AND_TABLE_NAME_LIST_STRING.split(",")),
    )
    db.session.add(rls)
    db.session.commit()
    logger.info(f'Created RLS {rls_name}')

  def fetch_all_database_tables_in_list(self, database_name, schema_and_table_name_list):
      return [table for table in [self.fetch_single_database_table(database_name, schema_and_table_name.split('|')[0], schema_and_table_name.split('|')[1]) for schema_and_table_name in schema_and_table_name_list] if table is not None]

  def fetch_single_database_table(self, database_name, schema, table_name):
    from superset.models.core import Database
    from superset.connectors.sqla.models import SqlaTable

    database = db.session.query(Database).filter_by(database_name=database_name).first()
    if not database:
      logger.error(f'Database {database_name} does not exist')
      return None

    table = (
        db.session.query(SqlaTable)
        .filter_by(
          table_name=table_name,
          schema=schema,
          database_id=database.id
        ).first()
    )
    if not table:
        logger.error(f'Table {table_name} does not exist in schema {schema} of database {database_name}')
        return None
    return table

  def build_dept_position_type_orgs_rls_clause(self, user_identifier, organization_id, headers: dict):
      debt_position_type_org_data = self.fetch_dept_position_type_orgs(user_identifier, organization_id, headers)
      debt_position_type_org_ids_string = self.build_debt_position_type_ids_string(debt_position_type_org_data)
      return f"organization_id = '{organization_id}' and debt_position_type_org_id in ({debt_position_type_org_ids_string})"

  def fetch_dept_position_type_orgs(self, user_identifier, organization_id, headers: dict):
    logger.info(f'Fetching DebtPositionTypeOrgs for user {user_identifier} and org {organization_id}')
    queryParamsDict = {"operatorExternalUserId": user_identifier, "organizationId": organization_id}
    response = requests.get(DEBT_POSITIONS_TYPE_ORG_URL, params=queryParamsDict, headers=headers, timeout=5, verify=False)
    response.raise_for_status()
    return response.json()

  def build_debt_position_type_ids_string(self, debt_position_type_org_data: dict):
    logger.debug(f'Extracting DebtPositionTypeOrgsId')
    dp_type_org_ids_string = ""
    for debt_position_type_org in debt_position_type_org_data.get("_embedded").get("debtPositionTypeOrgs"):
        if len(dp_type_org_ids_string) > 0:
            dp_type_org_ids_string += ","
        dp_type_org_ids_string += "'"
        dp_type_org_ids_string += str(debt_position_type_org.get("debtPositionTypeOrgId"))
        dp_type_org_ids_string += "'"
    return dp_type_org_ids_string

class CustomSecurityManager(SupersetSecurityManager):
    authdbview = CustomAuthView
    def __init__(self, appbuilder):
        super(CustomSecurityManager, self).__init__(appbuilder)