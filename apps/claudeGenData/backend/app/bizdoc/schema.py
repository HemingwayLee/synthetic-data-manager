"""Business document types and the variations a user can choose for each.

This is the single source of truth: the frontend renders the Settings form from it, and the
generator validates and resolves settings against it.

Field types:
  select       one value; "random" (the default unless noted) is resolved by the backend per document
  multiselect  zero or more values, used exactly as chosen
  text         free text
"""

from typing import Any

RANDOM = "random"


def select(id: str, label: str, options: list[str], section: str, default: str = RANDOM) -> dict[str, Any]:
    return {"id": id, "label": label, "type": "select", "options": options, "default": default, "section": section}


def multiselect(id: str, label: str, options: list[str], section: str, default: list[str] | None = None) -> dict[str, Any]:
    return {"id": id, "label": label, "type": "multiselect", "options": options, "default": default or [], "section": section}


def text(id: str, label: str, section: str, placeholder: str = "") -> dict[str, Any]:
    return {"id": id, "label": label, "type": "text", "default": "", "placeholder": placeholder, "section": section}


# Sections, in display order.
DOCUMENT, PARTIES, AMOUNTS, STYLE, LABELS, EXTRA = (
    "Document", "Parties", "Amounts & tax", "Format & style", "Training labels", "Extra",
)

# --- Fields shared by several document types -------------------------------------------------

ISSUER_TYPE = select("issuer_type", "Issuer type (発行者)", ["株式会社", "合同会社", "有限会社", "一般社団法人", "個人事業主"], PARTIES)
INDUSTRY = select(
    "industry", "Industry (業種)",
    ["IT・ソフトウェア", "製造", "建設", "不動産", "小売", "卸売", "飲食", "医療・介護", "物流・運輸",
     "広告・メディア", "コンサルティング", "教育", "人材サービス", "デザイン・クリエイティブ"],
    PARTIES,
)
RECIPIENT_TYPE = select("recipient_type", "Recipient (宛名)", ["法人（御中）", "法人担当者（様）", "個人（様）"], PARTIES)

ISSUE_PERIOD = select("issue_period", "Issue date range (発行日)", ["直近3か月", "直近1年", "1〜3年前", "3〜7年前"], DOCUMENT)
DATE_FORMAT = select("date_format", "Date format (日付表記)", ["和暦（令和・平成）", "西暦（YYYY年M月D日）", "西暦（YYYY/MM/DD）"], STYLE)
NUMBER_STYLE = select("number_style", "Digits (数字)", ["半角数字", "全角数字"], STYLE)
FONT = select("font", "Font (書体)", ["明朝体", "ゴシック体"], STYLE)
SEAL = select("seal", "Seal (印影)", ["角印", "丸印", "なし"], STYLE)
LAYOUT = select("layout", "Layout (レイアウト)", ["クラシック（罫線表）", "モダン（余白多め）", "ミニマル", "伝統的（枠囲み）"], STYLE)

TAX_RATES = select("tax_rates", "Tax rates (税率)", ["10%のみ", "8%（軽減税率）のみ", "10%と8%の混在"], AMOUNTS)
TAX_DISPLAY = select("tax_display", "Tax display (税表示)", ["税抜表示", "税込表示"], AMOUNTS)
ITEM_COUNT = select("item_count", "Line items (明細行数)", ["1〜3行", "4〜8行", "9〜15行"], AMOUNTS)
ITEM_KIND = select("item_kind", "Item kind (明細の種類)", ["商品", "サービス・役務", "商品とサービスの混在"], AMOUNTS)
AMOUNT_RANGE = select("amount_range", "Total amount (合計金額)", ["〜10万円", "10万〜100万円", "100万〜1,000万円", "1,000万円以上"], AMOUNTS)
PAYMENT_TERMS = select(
    "payment_terms", "Payment terms (支払条件)",
    ["月末締め翌月末払い", "月末締め翌々月末払い", "請求日から30日以内", "納品後即時"],
    AMOUNTS,
)

EXTRA_INSTRUCTIONS = text("extra_instructions", "Extra instructions", EXTRA, "例：建設業らしい専門用語を多めに")

# --- Document types --------------------------------------------------------------------------

DOC_TYPES: list[dict[str, Any]] = [
    {
        "id": "contracts",
        "label": "Contracts",
        "ja": "契約書",
        "fields": [
            select(
                "contract_type", "Contract type (契約の種類)",
                ["業務委託契約書", "準委任契約書", "請負契約書", "秘密保持契約書", "売買契約書", "継続的取引基本契約書",
                 "不動産賃貸借契約書", "金銭消費貸借契約書", "雇用契約書", "業務提携契約書", "代理店契約書",
                 "ソフトウェアライセンス契約書", "保守サービス契約書", "顧問契約書"],
                DOCUMENT,
            ),
            select("length", "Length (分量)", ["短い（5〜8条）", "標準（10〜15条）", "長い（20〜30条）"], DOCUMENT),
            select("numbering", "Numbering (条番号の構成)", ["条のみ", "条・項", "条・項・号"], DOCUMENT),
            select("tone", "Tone (文体)", ["標準的", "堅い・古風", "平易"], DOCUMENT),
            ISSUE_PERIOD,
            select("party_count", "Parties (当事者数)", ["2者（甲・乙）", "3者（甲・乙・丙）"], PARTIES),
            select("party_types", "Party types (当事者の種類)", ["法人と法人", "法人と個人", "個人と個人"], PARTIES),
            INDUSTRY,
            select(
                "jurisdiction", "Jurisdiction (管轄裁判所)",
                ["東京地方裁判所", "大阪地方裁判所", "名古屋地方裁判所", "福岡地方裁判所", "札幌地方裁判所", "仙台地方裁判所", "広島地方裁判所"],
                PARTIES,
            ),
            select("amount_style", "Amounts (金額表記)", ["算用数字（1,000,000円）", "漢数字（金百万円）", "大字（金壱百萬円）"], AMOUNTS),
            multiselect(
                "optional_sections", "Include sections (含める条項・欄)",
                ["記名押印欄", "収入印紙欄", "別紙（業務内容・仕様）", "反社会的勢力の排除", "秘密保持", "損害賠償の上限",
                 "契約の自動更新", "中途解約", "再委託", "知的財産権の帰属"],
                DOCUMENT,
                default=["記名押印欄", "反社会的勢力の排除", "秘密保持"],
            ),
            DATE_FORMAT, NUMBER_STYLE, FONT, SEAL,
            multiselect(
                "planted_issues", "Planted issues (意図的な不備)",
                ["管轄条項の欠落", "日付の矛盾", "金額の不一致", "一方的に不利な損害賠償条項", "解除条項の欠落",
                 "当事者名の表記ゆれ", "条番号の飛び・重複", "署名欄の不備"],
                LABELS,
            ),
            EXTRA_INSTRUCTIONS,
        ],
    },
    {
        "id": "invoices",
        "label": "Invoices",
        "ja": "請求書",
        "fields": [
            select("qualified_invoice", "Invoice kind (請求書の区分)", ["適格請求書（登録番号あり）", "区分記載請求書（登録番号なし）"], DOCUMENT),
            ISSUE_PERIOD,
            ISSUER_TYPE, INDUSTRY, RECIPIENT_TYPE,
            ITEM_COUNT, ITEM_KIND, AMOUNT_RANGE, TAX_RATES, TAX_DISPLAY,
            select("rounding", "Tax rounding (端数処理)", ["切り捨て", "四捨五入", "切り上げ"], AMOUNTS),
            select("withholding", "Withholding tax (源泉徴収)", ["なし", "あり（個人への報酬）"], AMOUNTS),
            PAYMENT_TERMS,
            select("bank_details", "Bank details (振込先)", ["あり（振込手数料はお客様負担）", "あり（手数料の記載なし）", "なし"], AMOUNTS),
            select("remarks", "Remarks (備考欄)", ["なし", "あり"], DOCUMENT),
            LAYOUT, DATE_FORMAT, NUMBER_STYLE, FONT, SEAL,
            multiselect(
                "planted_issues", "Planted issues (意図的な不備)",
                ["合計金額の計算誤り", "消費税額の計算誤り", "税率の誤り", "登録番号の欠落・桁不足", "支払期限が発行日より前", "宛名の誤記"],
                LABELS,
            ),
            EXTRA_INSTRUCTIONS,
        ],
    },
    {
        "id": "quotations",
        "label": "Quotations",
        "ja": "見積書",
        "fields": [
            select("validity", "Valid for (有効期限)", ["発行日から14日間", "発行日から30日間", "発行日から60日間", "発行日から90日間"], DOCUMENT),
            select("delivery", "Delivery (納期)", ["受注後1週間以内", "受注後2〜4週間", "別途協議", "指定日納品"], DOCUMENT),
            select("conditions", "Conditions (見積条件・備考)", ["なし", "あり"], DOCUMENT),
            select("show_registration_number", "Registration no. (登録番号)", ["記載あり", "記載なし"], DOCUMENT),
            ISSUE_PERIOD,
            ISSUER_TYPE, INDUSTRY, RECIPIENT_TYPE,
            ITEM_COUNT, ITEM_KIND, AMOUNT_RANGE, TAX_RATES, TAX_DISPLAY,
            select("discount", "Discount (値引き)", ["なし", "値引き行あり", "出精値引き"], AMOUNTS),
            PAYMENT_TERMS,
            LAYOUT, DATE_FORMAT, NUMBER_STYLE, FONT, SEAL,
            multiselect(
                "planted_issues", "Planted issues (意図的な不備)",
                ["合計金額の計算誤り", "消費税額の計算誤り", "数量×単価の不一致", "有効期限の欠落", "宛名の誤記"],
                LABELS,
            ),
            EXTRA_INSTRUCTIONS,
        ],
    },
    {
        "id": "receipts",
        "label": "Receipts",
        "ja": "領収書",
        "fields": [
            select("receipt_format", "Format (形式)", ["単票（フォーマル）", "レシート（POS・幅狭）", "手書き風"], DOCUMENT),
            select("qualified_receipt", "Receipt kind (区分)", ["適格簡易請求書（登録番号あり）", "登録番号なし"], DOCUMENT),
            select("purpose", "Purpose (但し書き)", ["具体的な品目", "品代として", "お食事代として", "空欄"], DOCUMENT),
            ISSUE_PERIOD,
            ISSUER_TYPE, INDUSTRY,
            select("recipient", "Addressee (宛名)", ["法人名（御中）", "個人名（様）", "上様", "空欄"], PARTIES),
            select("amount_range", "Amount (金額)", ["〜5千円", "5千〜5万円", "5万〜100万円", "100万円以上"], AMOUNTS),
            select("payment_method", "Payment method (支払方法)", ["現金", "クレジットカード", "銀行振込", "電子マネー・QR決済"], AMOUNTS),
            TAX_RATES,
            select("revenue_stamp", "Revenue stamp (収入印紙)", ["自動（金額と支払方法で判断）", "あり", "なし"], AMOUNTS),
            DATE_FORMAT, NUMBER_STYLE, FONT, SEAL,
            multiselect(
                "planted_issues", "Planted issues (意図的な不備)",
                ["収入印紙の貼付漏れ", "合計金額の計算誤り", "消費税額の誤り", "但し書きの不備", "日付の欠落"],
                LABELS,
            ),
            EXTRA_INSTRUCTIONS,
        ],
    },
]

SECTIONS = [DOCUMENT, PARTIES, AMOUNTS, STYLE, LABELS, EXTRA]


def find_doc_type(doc_type_id: str) -> dict[str, Any] | None:
    return next((d for d in DOC_TYPES if d["id"] == doc_type_id), None)


def validate_settings(doc_type: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    """Return clean settings (defaults filled in), raising ValueError on unknown values."""
    clean: dict[str, Any] = {}
    for field in doc_type["fields"]:
        value = settings.get(field["id"], field["default"])
        if field["type"] == "select":
            if value != RANDOM and value not in field["options"]:
                raise ValueError(f"{field['id']}: invalid option {value!r}")
        elif field["type"] == "multiselect":
            if not isinstance(value, list) or any(v not in field["options"] for v in value):
                raise ValueError(f"{field['id']}: invalid options {value!r}")
        elif field["type"] == "text":
            if not isinstance(value, str) or len(value) > 2000:
                raise ValueError(f"{field['id']}: must be text up to 2000 characters")
        clean[field["id"]] = value
    return clean
