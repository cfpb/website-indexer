from rest_framework import serializers

from warc.models import Component, Error, Page, Redirect


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ["class_name"]


class RequestSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    url = serializers.CharField()


class PageSerializer(RequestSerializer):
    title = serializers.CharField()
    language = serializers.CharField()


class PageWithComponentSerializer(PageSerializer):
    class_name = serializers.CharField(source="components__class_name")


class PageWithLinkSerializer(PageSerializer):
    href = serializers.CharField(source="links__href")


class PageDetailSerializer(serializers.ModelSerializer):
    components = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="class_name"
    )

    links = serializers.SlugRelatedField(many=True, read_only=True, slug_field="href")

    class Meta:
        model = Page
        fields = [
            "timestamp",
            "url",
            "title",
            "language",
            "text",
            "html",
            "components",
            "links",
        ]


class ErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Error
        fields = ["timestamp", "url", "status_code", "referrer"]


class RedirectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redirect
        fields = ["timestamp", "url", "status_code", "referrer", "location"]
