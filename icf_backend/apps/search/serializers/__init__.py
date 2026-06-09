from rest_framework import serializers


class SearchResultSerializer(serializers.Serializer):
    entity_type = serializers.CharField()
    entity_id = serializers.IntegerField()
    label = serializers.CharField()
    sublabel = serializers.CharField()
    url_hint = serializers.CharField()
    extra = serializers.DictField(child=serializers.CharField(), default=dict)
