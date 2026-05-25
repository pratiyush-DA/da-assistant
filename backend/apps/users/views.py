from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.neo4j.repositories.user import UserRepository

from .serializers import UserSerializer, UserUpdateSerializer


class UserListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        q = request.query_params.get("q")
        users = UserRepository().list_all(query=q)
        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repo = UserRepository()
        email = serializer.validated_data["email"]
        if repo.get_by_email(email):
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = repo.create(
            email=email,
            display_name=serializer.validated_data["display_name"],
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserSearchView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        q = request.query_params.get("q", "")
        users = UserRepository().search(q)
        return Response(UserSerializer(users, many=True).data)


class UserDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request, pk):
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        repo = UserRepository()
        if not repo.exists(str(pk)):
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = serializer.validated_data
        if "email" in data and repo.get_by_email(data["email"]):
            existing = repo.get_by_email(data["email"])
            if existing and existing["id"] != str(pk):
                return Response(
                    {"detail": "Email already in use."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        user = repo.update(
            str(pk),
            email=data.get("email"),
            display_name=data.get("display_name"),
        )
        return Response(UserSerializer(user).data)
