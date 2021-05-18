from django.db import models
from rest_framework import serializers, viewsets, routers
from drf_spectacular.generators import SchemaGenerator


class User(models.Model):
    email = models.EmailField()
    is_active = models.BooleanField()
    phone = models.CharField(max_length=20)
    first = models.CharField(max_length=20, blank=True, null=True)


class Receiver(models.Model):
    receiver = models.ForeignKey(
        User,
        verbose_name="Receiver Profile",
        on_delete=models.SET_NULL,
    )


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class UserSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first",
            "email",
            "is_active",
            "phone",
        ]


class ReceiverSerializer(DynamicFieldsModelSerializer):
    receiver = UserSerializer(fields=("first", "email"))

    class Meta:
        model = Receiver
        fields = [
            "receiver",
        ]


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.none()


class ReceiverViewSet(viewsets.ModelViewSet):
    serializer_class = ReceiverSerializer
    queryset = Receiver.objects.none()


def test_dynamic_models():
    router = routers.SimpleRouter()
    router.register('y/', UserViewSet, basename='y/')
    router.register('z/', ReceiverViewSet, basename='z/')
    generator = SchemaGenerator(patterns=router.urls)
    schema = generator.get_schema(request=None, public=True)

    # Assert user schema is returned for user response
    user_response = schema['paths']['/y//']['get']['responses']['200']['content']['application/json']['schema']['items']['$ref']
    assert user_response == "#/components/schemas/User"

    # Assert same user schema is returned for receiver response
    receiver_response = schema['paths']['/z//']['get']['responses']['200']['content']['application/json']['schema']['items']['$ref']
    assert receiver_response == "#/components/schemas/Receiver"

    receiver_user_schema = schema['components']['schemas']['Receiver']['properties']['receiver']['$ref']
    assert receiver_user_schema == "#/components/schemas/User"

    # Assert all properties are included for both (undesired)
    user_schema = schema['components']['schemas']['User']
    assert len(user_schema['properties']) == 5
