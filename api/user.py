from db.models import User, History


def create_user(id_: int, name: str, username: str, status: str = 'main_menu', role: str = 'user') -> dict:
    u = User.create(id=id_, name=name, username=username, status=status, role=role)


def get_user(id: int) -> dict:
    u = User.get(id=id)
    return u.get_as_dict()


def get_user_by_username(username: str) -> dict:
    u = User.get(username=username)
    return u.get_as_dict()


def is_admin(id: int) -> bool:
    u = User.get(id=id)
    return u.role == 'admin'


def is_exists(id: int) -> bool:
    try:
        User.get(id=id)
    except User.DoesNotExist:
        return False
    return True


def is_verified(id: int) -> bool:
    u = User.get(id=id)
    return u.role in ['member', 'admin']


def verify_user(id: int) -> bool:
    u = User.get(id=id)
    u.role = 'member'
    u.save()
    return True


def get_user_equipment(id: int) -> list:
    res = []
    u = User.get(id=id)
    for eq in u.equipment:
        pick_date = History.select().where(History.equipment == eq).order_by(History.id.desc()).get().date.date()
        res.append({'id': eq.id, 'name': eq.name, 'picked': pick_date})
    return res


def get_admin_list() -> list:
    res = []
    for admin in User.select().where(User.role == 'admin'):
        res.append(admin.get_as_dict())
    return res
