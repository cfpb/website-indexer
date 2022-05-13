from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(label="Search", required=False)
    search_type = forms.ChoiceField(
        choices=(
            (c, c)
            for c in (
                "links",
                "html",
                "components",
            )
        ),
    )
    paginate_by = forms.ChoiceField(
        choices=(
            (c, c)
            for c in (
                "50",
                "100",
                "200",
            )
        ),
    )
