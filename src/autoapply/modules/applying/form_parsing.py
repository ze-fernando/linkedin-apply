from selectolax.lexbor import LexborHTMLParser, LexborNode

from autoapply.modules.applying.models import FieldKind, FormField, FormStep, StepAction

FIELD_CONTAINER_SELECTOR = ".fb-dash-form-element"
CURRENT_VALUE_ATTRIBUTE = "data-autoapply-value"
CHECKED_ATTRIBUTE = "data-autoapply-checked"
RADIO_GROUP_SELECTOR = "fieldset[data-test-form-builder-radio-button-form-component]"
RADIO_TITLE_SELECTOR = "[data-test-form-builder-radio-button-form-component__title]"
RADIO_REQUIRED_SELECTOR = "[data-test-form-builder-radio-button-form-component__required]"
RADIO_OPTION_ATTRIBUTE = "data-test-text-selectable-option__input"
NUMBER_ID_SUFFIX = "-numeric"
PHONE_ID_MARKER = "phoneNumber-nationalNumber"
PHONE_COUNTRY_ID_MARKER = "phoneNumber-country"
LOCATION_TYPEAHEAD_SELECTOR = "[data-test-single-typeahead-entity-form-component]"
RESUME_UPLOAD_SELECTOR = 'input[type="file"][id*="upload-resume"]'
FOLLOW_COMPANY_SELECTOR = "#follow-company-checkbox"
ERROR_MESSAGE_SELECTOR = ".artdeco-inline-feedback--error .artdeco-inline-feedback__message"
ACTION_SELECTORS = {
    StepAction.SUBMIT: "button[data-live-test-easy-apply-submit-button]",
    StepAction.REVIEW: "button[data-live-test-easy-apply-review-button]",
    StepAction.NEXT: "button[data-easy-apply-next-button]",
}
SELECT_PLACEHOLDERS = {"selecionar opção", "select an option", "selecciona una opción"}


def collapse_text(text: str) -> str:
    return " ".join(text.split())


def read_current_value(element: LexborNode) -> str | None:
    value = collapse_text(element.attributes.get(CURRENT_VALUE_ATTRIBUTE) or "")
    return value if value and value.casefold() not in SELECT_PLACEHOLDERS else None


def is_required(element: LexborNode) -> bool:
    return "required" in element.attributes or element.attributes.get("aria-required") == "true"


def find_label(container: LexborNode, element_id: str) -> str:
    for label in container.css("label"):
        if label.attributes.get("for") == element_id:
            return collapse_text(label.text())
    return ""


def find_text_kind(element_id: str) -> FieldKind:
    if element_id.endswith(NUMBER_ID_SUFFIX):
        return FieldKind.NUMBER
    if PHONE_ID_MARKER in element_id:
        return FieldKind.PHONE
    return FieldKind.TEXT


def parse_text_input(container: LexborNode, element: LexborNode, kind: FieldKind | None = None) -> FormField:
    element_id = element.attributes.get("id") or ""
    return FormField(
        element_id=element_id,
        kind=kind or find_text_kind(element_id),
        label=find_label(container, element_id),
        required=is_required(element),
        value=read_current_value(element),
        options=[],
    )


def parse_select(container: LexborNode, element: LexborNode) -> FormField:
    element_id = element.attributes.get("id") or ""
    options = [collapse_text(option.text()) for option in element.css("option")]
    return FormField(
        element_id=element_id,
        kind=FieldKind.PHONE_COUNTRY if PHONE_COUNTRY_ID_MARKER in element_id else FieldKind.SELECT,
        label=find_label(container, element_id),
        required=is_required(element),
        value=read_current_value(element),
        options=[option for option in options if option.casefold() not in SELECT_PLACEHOLDERS],
    )


def parse_radio_group(group: LexborNode) -> FormField:
    inputs = group.css(f"input[{RADIO_OPTION_ATTRIBUTE}]")
    checked = [radio for radio in inputs if radio.attributes.get(CHECKED_ATTRIBUTE) == "true"]
    title = group.css_first(RADIO_TITLE_SELECTOR)
    required = group.css_first(RADIO_REQUIRED_SELECTOR) is not None or any(is_required(radio) for radio in inputs)
    return FormField(
        element_id=group.attributes.get("id") or "",
        kind=FieldKind.RADIO,
        label=collapse_text(title.text()) if title else "",
        required=required,
        value=checked[0].attributes.get(RADIO_OPTION_ATTRIBUTE) if checked else None,
        options=[radio.attributes.get(RADIO_OPTION_ATTRIBUTE) or "" for radio in inputs],
    )


def parse_textarea(container: LexborNode, element: LexborNode) -> FormField:
    element_id = element.attributes.get("id") or ""
    return FormField(
        element_id=element_id,
        kind=FieldKind.FREE_TEXT,
        label=find_label(container, element_id),
        required=is_required(element),
        value=read_current_value(element),
        options=[],
    )


def parse_unknown_group(group: LexborNode) -> FormField:
    legend = group.css_first("legend")
    return FormField(
        element_id=group.attributes.get("id") or "",
        kind=FieldKind.UNKNOWN,
        label=collapse_text(legend.text()) if legend else "",
        required=any(is_required(element) for element in group.css("input")),
        value=None,
        options=[],
    )


def parse_unknown_input(container: LexborNode, element: LexborNode) -> FormField:
    element_id = element.attributes.get("id") or ""
    return FormField(
        element_id=element_id,
        kind=FieldKind.UNKNOWN,
        label=find_label(container, element_id),
        required=is_required(element),
        value=None,
        options=[],
    )


def is_plain_text_input(element: LexborNode) -> bool:
    return element.attributes.get("type") == "text" and element.attributes.get("role") != "combobox"


def parse_field(container: LexborNode) -> FormField | None:
    radio_group = container.css_first(RADIO_GROUP_SELECTOR)
    if radio_group is not None:
        return parse_radio_group(radio_group)
    other_group = container.css_first("fieldset")
    if other_group is not None:
        return parse_unknown_group(other_group)
    select = container.css_first("select")
    if select is not None:
        return parse_select(container, select)
    textarea = container.css_first("textarea")
    if textarea is not None:
        return parse_textarea(container, textarea)
    element = container.css_first("input")
    if element is None:
        return None
    if is_plain_text_input(element):
        return parse_text_input(container, element)
    if container.css_first(LOCATION_TYPEAHEAD_SELECTOR) is not None and element.attributes.get("role") == "combobox":
        return parse_text_input(container, element, FieldKind.LOCATION)
    return parse_unknown_input(container, element)


def find_action(tree: LexborHTMLParser) -> StepAction | None:
    return next((action for action, selector in ACTION_SELECTORS.items() if tree.css_first(selector)), None)


def parse_form_step(html: str) -> FormStep:
    tree = LexborHTMLParser(html)
    title = tree.css_first("h3")
    fields = [parse_field(container) for container in tree.css(FIELD_CONTAINER_SELECTOR)]
    return FormStep(
        title=collapse_text(title.text()) if title else "",
        fields=[field for field in fields if field is not None],
        has_resume_upload=tree.css_first(RESUME_UPLOAD_SELECTOR) is not None,
        has_follow_company=tree.css_first(FOLLOW_COMPANY_SELECTOR) is not None,
        action=find_action(tree),
        errors=[collapse_text(message.text()) for message in tree.css(ERROR_MESSAGE_SELECTOR)],
    )
