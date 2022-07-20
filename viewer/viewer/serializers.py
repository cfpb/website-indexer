from rest_framework import serializers

from warc.models import Component, Error, Page, Redirect


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ["class_name"]


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["timestamp", "url"]


class PageSerializer(RequestSerializer):
    class Meta:
        model = Page
        fields = RequestSerializer.Meta.fields + ["title", "language"]


class ErrorSerializer(RequestSerializer):
    class Meta:
        model = Error
        fields = RequestSerializer.Meta.fields + ["status_code", "referrer"]


class RedirectSerializer(ErrorSerializer):
    class Meta:
        model = Redirect
        fields = ErrorSerializer.Meta.fields + ["location"]
