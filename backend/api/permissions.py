import abc


class BasePermission(metaclass=abc.ABCMeta):
    """
    A base class from which all permission classes should inherit.
    """

    @abc.abstractmethod
    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        raise NotImplementedError()


class IsAuthenticatedForObject(BasePermission):
    """
    Allows access only to authenticated users with the same identifier as the resource identifier.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request['payload'].get('id') == view.object_id
