from re import M
from rest_framework import pagination


class BetterPageNumberPagination(pagination.PageNumberPagination):
    """PageNumberPagination that includes page number information."""

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data.update(
            {
                "num_pages": self.page.paginator.num_pages,
                "page_number": self.page.number,
            }
        )
        return response

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema["properties"].update(
            {
                "num_pages": {
                    "type": "integer",
                    "example": 10,
                },
                "page_number": {
                    "type": "integer",
                    "example": 5,
                },
            }
        )
        return schema
