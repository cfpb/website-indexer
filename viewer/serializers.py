import re

from rest_framework import serializers

from crawler.models import Component, Error, Page, Redirect


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ["class_name"]


class RequestSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    url = serializers.CharField()


PAGE_TITLE_SUFFIX_RE = re.compile(
    r" \| ("
    r"Consumer Financial Protection Bureau|"
    r"Oficina para la Protección Financiera del Consumidor"
    r")$"
)


class PageSerializer(RequestSerializer):
    title = serializers.SerializerMethodField()
    language = serializers.CharField()

    class Meta:
        csv_header = ["url", "title", "language"]

    def get_title(self, obj):
        return PAGE_TITLE_SUFFIX_RE.sub("", obj["title"])


class PageWithComponentSerializer(PageSerializer):
    class_name = serializers.CharField(source="components__class_name")

    class Meta:
        csv_header = PageSerializer.Meta.csv_header + ["class_name"]


class PageWithLinkSerializer(PageSerializer):
    link_url = serializers.CharField(source="links__href")

    class Meta:
        csv_header = PageSerializer.Meta.csv_header + ["link_url"]


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
        csv_header = ["url", "status_code", "referrer"]


class RedirectSerializer(serializers.ModelSerializer):
    redirect_url = serializers.CharField(source="location")

    class Meta:
        model = Redirect
        fields = ErrorSerializer.Meta.fields + [
            "redirect_url",
            "is_http_to_https",
            "is_append_slash",
        ]
        csv_header = ErrorSerializer.Meta.csv_header + [
            "redirect_url",
            "is_http_to_https",
            "is_append_slash",
        ]
