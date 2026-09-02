from __future__ import annotations


class TextWorkflowError(Exception):
    """TextWorkflow パッケージが発生させる例外の共通基底。

    TextWorkflow.execute() は原則として例外を発生させず、
    WorkflowResult (status=REJECTED/FAILED) を返す Result パターンを採用する。
    本例外は内部コンポーネント (TemplateRenderer 等) が予期しない状態を
    検出した場合に発生し、TextWorkflow 内部で捕捉されて WorkflowResult へ
    変換されることを原則とする。

    呼び出し側が個別の内部例外型を意識せず捕捉できるよう、内部で新設する
    例外は本クラスを継承する。
    """
