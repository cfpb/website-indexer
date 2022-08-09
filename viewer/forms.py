from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(label="Search", required=False)
    search_type = forms.ChoiceField(
        choices=(
            (c, c)
            for c in (
                "title",
                "url",
                "components",
                "links",
                "text",
                "html",
            )
        ),
    )
