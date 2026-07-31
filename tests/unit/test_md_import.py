from app.domain.md_import import parse_markdown_faq


def test_h1_split():
    md = "# 如何重置密码\n登录页点忘记密码。\n\n# 如何退款\n订单页申请退款。"
    items = parse_markdown_faq(md)
    assert len(items) == 2
    assert items[0].title == "如何重置密码"
    assert "忘记密码" in items[0].content
    assert items[1].title == "如何退款"


def test_h2_split_when_no_h1():
    md = "## Reset password\nTap forgot password.\n\n## Refund\nOpen order details."
    items = parse_markdown_faq(md)
    assert len(items) == 2
    assert items[0].title == "Reset password"


def test_intro_before_first_heading_ignored():
    md = "这是一份 FAQ 文档介绍。\n\n# 标题A\n正文A"
    items = parse_markdown_faq(md)
    assert len(items) == 1
    assert items[0].title == "标题A"


def test_subheadings_kept_in_content():
    md = "# 支付问题\n### 充值\n充值说明\n### 退款\n退款说明\n# 账号问题\n账号说明"
    items = parse_markdown_faq(md)
    assert len(items) == 2
    assert "### 充值" in items[0].content
    assert "### 退款" in items[0].content


def test_empty_content_skipped():
    md = "# 空条目\n\n# 有内容\n正文"
    items = parse_markdown_faq(md)
    assert len(items) == 1
    assert items[0].title == "有内容"


def test_hash_in_code_fence_not_heading():
    md = "# 真标题\n```\n# 这是代码注释不是标题\n```\n代码说明"
    items = parse_markdown_faq(md)
    assert len(items) == 1
    assert items[0].title == "真标题"
    assert "# 这是代码注释不是标题" in items[0].content


def test_no_heading_returns_empty():
    assert parse_markdown_faq("纯文本没有标题") == []
    assert parse_markdown_faq("") == []
