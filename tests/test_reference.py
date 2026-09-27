from PIL import Image

from mcbuild.agent.reference import (
    _extract_json_object,
    analyze_reference,
    critique_reference,
    fit_image_for_model,
)
from mcbuild.llm.fake import FakeLLM


def test_fit_image_for_model_caps_long_edge_without_upscaling():
    large = Image.new("RGB", (1600, 900), (1, 2, 3))
    fitted = fit_image_for_model(large, 1024)
    assert fitted.size == (1024, 576)

    small = Image.new("RGB", (320, 200), (1, 2, 3))
    untouched = fit_image_for_model(small, 1024)
    assert untouched.size == small.size


def test_extract_json_object_tolerates_fenced_output():
    parsed = _extract_json_object("""```json
{"version": 1, "priority_constraints": ["silhouette"]}
```""")
    assert parsed == {"version": 1, "priority_constraints": ["silhouette"]}


def test_reference_analysis_and_critic_are_stateless_for_fake_builder():
    llm = FakeLLM()
    ref = Image.new("RGB", (1024, 768), (80, 80, 80))

    spec = analyze_reference(llm, "fake/model", "a castle", ref)
    assert spec["parse_status"] == "ok"
    assert spec["version"] == 1
    assert llm._step == 0

    render = Image.new("RGB", (640, 480), (40, 40, 40))
    critique = critique_reference(
        llm,
        "fake/model",
        ref,
        spec,
        [("yaw 0deg", render)],
        {"dims": (20, 20, 20), "block_count": 100, "top_materials": []},
    )
    assert critique["parse_status"] == "ok"
    assert "next_focus" in critique
    assert llm._step == 0
