import logging
import os
import jwt
from jwt import DecodeError
from superset.security import SupersetSecurityManager
from flask import flash
import requests
from flask_appbuilder.security.views import AuthDBView
from flask_appbuilder.security.views import expose
from flask_login import login_user
from flask import request, redirect
from configs.role_and_permission_manager import RoleAndPermissionManager
from configs.dto.pu_user_info_dto import PUUserInfo

USERINFO_URL = os.environ.get('AUTH_BASE_URL') + "/oauth/userinfo"
logger = logging.getLogger(__name__)

class CustomAuthView(AuthDBView):
  login_template = 'appbuilder/general/security/login_db.html'

  def __init__(self):
      super(CustomAuthView, self).__init__()
      self.role_and_permission_manager = RoleAndPermissionManager()

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
                response = requests.get(USERINFO_URL, headers=headers, timeout=5)
                response.raise_for_status()
                user_data = response.json()
                user_identifier = user_data.get('mappedExternalUserId')
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
                        self.role_and_permission_manager.manage_user_roles_and_permissions(
                            self.appbuilder.sm,
                            user,
                            PUUserInfo.build_pu_user_info(user_data),
                            headers
                        )
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

class CustomSecurityManager(SupersetSecurityManager):
    authdbview = CustomAuthView
    def __init__(self, appbuilder):
        super(CustomSecurityManager, self).__init__(appbuilder)