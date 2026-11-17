"""The tutorial script: what is said and what happens on screen in each scene.

narration  what macOS `say` speaks (English UI names spelled in katakana so they're pronounced well)
subtitle   what is shown on screen (keeps the real UI names); split into cues at 。
action     drives the browser while the narration plays; the scene lasts at least as long as its audio

Edit the text here and re-run generate.py to change the video.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Scene:
    id: str
    narration: str
    subtitle: str
    action: Callable


def title(d):
    d.show_card(
        "<div class='eyebrow'>claudeGenData</div>"
        "<h1>ビジネス文書ジェネレーター<br>使い方ガイド</h1>"
        "<p>契約書・請求書・見積書・領収書の架空データを Claude Code で生成</p>"
    )


def open_menu(d):
    d.hide_card()
    d.wait(1.0)
    d.click(d.page.get_by_role("tab", name="Biz Doc"))
    d.wait(1.5)
    d.click(d.page.get_by_role("menuitem", name="Invoices"))


def settings_overview(d):
    d.wait(1.5)
    d.scroll(900, steps=3)
    d.wait(1.5)
    d.scroll(-900, steps=3)


def choose_values(d):
    d.wait(0.5)
    # These match the sample invoice shown later, so "Settings used" agrees with what was chosen.
    d.choose(r"^Tax rates", "10%のみ")
    d.wait(0.8)
    d.choose(r"^Layout", "クラシック（罫線表）")


def planted_issues(d):
    chip = d.page.get_by_role("button", name="消費税額の計算誤り")
    d.wait(0.5)
    d.click(chip)
    d.wait(3.5)
    d.click(chip)  # deselect: the sample invoice has no planted issues


def generate(d):
    d.wait(1.0)
    d.click(d.page.get_by_role("button", name="Generate", exact=True))
    d.wait(2.0)
    d.click(d.page.get_by_role("button", name="View results"))


def results(d):
    d.wait(3.0)
    d.mock.finish_running(1)
    d.wait(3.5)  # the Results page polls every 3 seconds


def label_tabs(d):
    d.wait(0.5)
    d.click(d.page.get_by_role("tab", name="Labels"))
    d.wait(4.0)
    d.click(d.page.get_by_role("tab", name="Settings used"))


def batch(d):
    d.wait(0.5)
    d.choose(r"^Documents", "10 請求書")
    d.wait(0.8)
    d.click(d.page.get_by_role("button", name="Batch Generation"))


def queue_and_cancel(d):
    d.wait(3.0)
    d.mock.finish_running(2)
    d.wait(3.5)
    d.click(d.page.get_by_role("button", name=d.re(r"^Cancel \d+ queued")))


def files(d):
    d.wait(0.5)
    d.show_card(
        "<h2>保存先</h2>"
        "<pre>data/bizdoc/invoices/101/\n"
        "  ├─ document.pdf    文書（PDF）\n"
        "  ├─ document.html   文書（HTML）\n"
        "  └─ labels.json     正解ラベルと使った設定</pre>"
    )


def ending(d):
    d.show_card("<h1>ありがとうございました</h1>")


SCENES = [
    Scene(
        "01_title",
        "このビデオでは、トークトゥークロードの、ビジネス文書ジェネレーターの使い方をご紹介します。"
        "契約書、請求書、見積書、領収書の架空データを、クロードコードで自動生成できます。",
        "このビデオでは、claudeGenData のビジネス文書ジェネレーターの使い方をご紹介します。"
        "契約書、請求書、見積書、領収書の架空データを、Claude Code で自動生成できます。",
        title,
    ),
    Scene(
        "02_menu",
        "まず、画面上部の、ビズドックタブをクリックします。メニューから文書の種類を選びます。今回は、請求書を選びましょう。",
        "まず、画面上部の「Biz Doc」タブをクリックします。メニューから文書の種類を選びます。今回は、請求書を選びましょう。",
        open_menu,
    ),
    Scene(
        "03_settings",
        "設定画面には、生成する文書のバリエーションが並んでいます。"
        "ランダムのままにした項目は、文書ごとに自動で選ばれるので、毎回ちがう文書ができあがります。",
        "設定画面には、生成する文書のバリエーションが並んでいます。"
        "「ランダム」のままにした項目は、文書ごとに自動で選ばれるので、毎回ちがう文書ができあがります。",
        settings_overview,
    ),
    Scene(
        "04_choose",
        "必要な項目だけを、指定することもできます。例えば、税率を、十パーセントのみに、レイアウトを、クラシックにしてみます。",
        "必要な項目だけを指定することもできます。例えば、税率を「10%のみ」に、レイアウトを「クラシック」にしてみます。",
        choose_values,
    ),
    Scene(
        "05_labels",
        "トレーニングラベルの欄では、意図的に埋め込む不備を選べます。選んだ不備は文書に入り、どこにあるかが、正解ラベルとして記録されます。"
        "今回は、不備なしで進めます。",
        "「Training labels」では、意図的に埋め込む不備を選べます。選んだ不備は文書に入り、どこにあるかが正解ラベルとして記録されます。"
        "今回は、不備なしで進めます。",
        planted_issues,
    ),
    Scene(
        "06_generate",
        "準備ができたら、画面下の、ジェネレートボタンを押します。生成はバックグラウンドで進み、通常は一分ほどで完了します。",
        "準備ができたら、画面下の「Generate」ボタンを押します。生成はバックグラウンドで進み、通常は1分ほどで完了します。",
        generate,
    ),
    Scene(
        "07_results",
        "結果画面では、生成の進み具合を確認できます。完成すると、文書のプレビューが表示されます。",
        "結果画面では、生成の進み具合を確認できます。完成すると、文書のプレビューが表示されます。",
        results,
    ),
    Scene(
        "08_tabs",
        "ラベルタブには、当事者、金額、重要な項目、埋め込んだ不備といった、正解データがまとめられています。"
        "セッティングスユーズドタブでは、実際に使われた設定を確認できます。",
        "「Labels」タブには、当事者、金額、重要な項目、埋め込んだ不備といった正解データがまとめられています。"
        "「Settings used」タブでは、実際に使われた設定を確認できます。",
        label_tabs,
    ),
    Scene(
        "09_batch",
        "たくさん作りたいときは、左側の、バッチジェネレーションを使います。件数を選んでボタンを押すと、今の設定で、まとめて生成します。",
        "たくさん作りたいときは、左側の「Batch Generation」を使います。件数を選んでボタンを押すと、今の設定でまとめて生成します。",
        batch,
    ),
    Scene(
        "10_queue",
        "生成は、同時に二件ずつ進み、残りは順番待ちになります。途中でやめたいときは、キャンセルキュードボタンで、待機中の文書を取り消せます。",
        "生成は同時に2件ずつ進み、残りは順番待ちになります。途中でやめたいときは「Cancel queued」で、待機中の文書を取り消せます。",
        queue_and_cancel,
    ),
    Scene(
        "11_files",
        "生成した文書は、データフォルダーの中に、ピーディーエフ、エイチティーエムエル、そして正解ラベルのジェイソンファイルとして保存されます。"
        "そのまま、学習データとして使えます。",
        "生成した文書は data/bizdoc フォルダーに、PDF、HTML、正解ラベルの JSON として保存されます。"
        "そのまま学習データとして使えます。",
        files,
    ),
    Scene(
        "12_end",
        "以上で、使い方の説明は終わりです。ぜひ、いろいろな設定で試してみてください。",
        "以上で、使い方の説明は終わりです。ぜひ、いろいろな設定で試してみてください。",
        ending,
    ),
]
