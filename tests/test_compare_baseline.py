from compare_baseline import top_k_overlap


def test_identical_lists_score_one():
    links = ["https://www.a.com/x/", "https://b.com/y"]
    assert top_k_overlap(links, ["https://a.com/x", "https://b.com/y"]) == 1.0


def test_query_strings_keep_pages_apart():
    old = ["https://www.youtube.com/watch?v=AAA"]
    new = ["https://youtube.com/watch?v=BBB"]
    assert top_k_overlap(old, new) == 0.0
