import os
from textwrap import shorten
from typing import Callable, Optional

from aeo_blog_engine.agents import (
    get_researcher_agent,
    get_planner_agent,
    get_writer_agent,
    get_optimizer_agent,
    get_base_model,
    get_reddit_agent,
    get_linkedin_agent,
    get_twitter_agent,
    get_social_qa_agent,
    get_topic_generator_agent,
)
from aeo_blog_engine.knowledge.knowledge_base import get_knowledge_base
from agno.agent import Agent


# ── Langfuse: optional, non-blocking ─────────────────────────────────────────
# The app runs normally when Langfuse keys are absent — tracing is silently skipped.

_langfuse_enabled = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
)

langfuse = None
_observe_impl = None

if _langfuse_enabled:
    try:
        from langfuse import Langfuse as _Langfuse, observe as _observe_impl
        langfuse = _Langfuse()
    except Exception as _lf_err:
        print(f"[INFO] Langfuse init failed — tracing disabled. ({_lf_err})")
        _observe_impl = None


def observe():
    """Decorator factory: wraps with Langfuse tracing when available, else a no-op."""
    if _observe_impl is not None:
        return _observe_impl()

    def _noop(fn):
        return fn

    return _noop


# ── Pipeline ──────────────────────────────────────────────────────────────────

class AEOBlogPipeline:
    def __init__(self):
        print("Initializing AEO Blog Pipeline with Agno Agents...")

    @observe()
    def run(self, topic: str = None, prompt: str = None, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if not topic and not prompt:
            raise ValueError("Either 'topic' or 'prompt' must be provided.")

        print("--- Starting AEO Blog Generation ---")

        total_input_tokens = 0
        total_output_tokens = 0

        # 0. Topic generation (if only prompt given)
        topic_gen_response = None
        if prompt and not topic:
            print(f"\n[0/5] Generating Topic from Prompt: '{prompt}'...")
            topic_generator = get_topic_generator_agent()
            topic_gen_response = topic_generator.run(
                f"Generate a blog topic for: {prompt}", stream=False
            )
            topic = topic_gen_response.content.strip()
            print(f"Generated Topic: {topic}")
            if progress_callback:
                progress_callback("topic_generator")

        print(f"Target Topic: {topic}")

        # 1. Research
        print("\n[1/5] Researching...")
        researcher = get_researcher_agent()
        research_response = researcher.run(
            f"Research key facts, statistics, and user questions about: {topic}",
            stream=False,
        )
        research_summary = (research_response.content or "").strip()

        if not _has_research_signal(research_summary):
            print("[WARN] Research output invalid/empty. Retrying with fallback prompt...")
            fallback_prompt = (
                f"Provide a concise research summary for '{topic}'. "
                "List at least five bullet points covering statistics, audience pain points, "
                "and common user questions."
            )
            try:
                fallback_response = researcher.run(fallback_prompt, stream=False)
                research_summary = (fallback_response.content or "").strip()
            except Exception as retry_exc:
                print(f"[WARN] Fallback research run failed: {retry_exc}")

        if not _has_research_signal(research_summary):
            print("[WARN] Using structured fallback research summary.")
            research_summary = _structured_fallback_research(topic)

        if progress_callback:
            progress_callback("researcher")

        # 2. Plan
        print("\n[2/5] Planning...")
        planner = get_planner_agent()
        plan_response = planner.run(
            f"Topic: '{topic}'\n\nResearch:\n{research_summary}", stream=False
        )
        plan = plan_response.content
        if progress_callback:
            progress_callback("planner")

        # 3. Write
        print("\n[3/5] Writing...")
        writer = get_writer_agent()
        draft_response = writer.run(
            f"Write the blog for '{topic}' using this outline:\n\n{plan}\n\nResearch:\n{research_summary}",
            stream=False,
        )
        draft = draft_response.content
        if progress_callback:
            progress_callback("writer")

        # 4. Optimize
        print("\n[4/5] Optimizing...")
        optimizer = get_optimizer_agent()
        opt_response = optimizer.run(f"Draft:\n{draft}", stream=False)
        optimization_report = opt_response.content
        if progress_callback:
            progress_callback("optimizer")

        # 5. Finalize
        print("\n[5/5] Finalizing...")
        finalizer = Agent(
            model=get_base_model(),
            instructions=[
                """You are the Final Editor. Produce the final, publish-ready markdown file.
1. Take the Draft and apply the improvements from the Optimization Report.
2. Ensure perfect Markdown formatting.
3. STRICTLY output ONLY the blog content — no preamble, no "Here is the blog" text."""
            ],
            markdown=True,
        )
        final_response = finalizer.run(
            f"Draft:\n{draft}\n\nOptimization Suggestions:\n{optimization_report}\n\nProduce the Final Blog Post.",
            stream=False,
        )

        if progress_callback:
            progress_callback("final_editor")

        # Langfuse token tracking (silent if not configured)
        _track_usage(
            name="Total_Pipeline_Usage",
            input_text=prompt if prompt else topic,
            output_text=final_response.content,
            responses=[r for r in [topic_gen_response, research_response, plan_response, draft_response, opt_response, final_response] if r],
            metadata={"source": "agno-agent-aggregation", "generated_topic": topic if prompt else None},
        )

        return final_response.content

    def generate_topic_only(self, prompt: str) -> str:
        """Generate a topic string from a raw prompt without running the full pipeline."""
        topic_generator = get_topic_generator_agent()
        response = topic_generator.run(f"Generate a blog topic for: {prompt}", stream=False)
        return response.content.strip()

    @observe()
    def run_social_post(self, topic: str, platform: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        print(f"--- Starting Social Post Generation for: {topic} ({platform}) ---")

        # 1. Research
        print("\n[1/3] Researching...")
        researcher = get_researcher_agent()
        research_response = researcher.run(
            f"Research key facts and trends about: {topic}", stream=False
        )
        research_summary = research_response.content
        print(f"Research completed ({len(research_summary)} chars).")
        if progress_callback:
            progress_callback("social_researcher")

        # 2. Write platform-specific post
        print(f"\n[2/3] Writing {platform} post...")
        platform_lower = platform.lower()
        if platform_lower == "reddit":
            writer = get_reddit_agent()
        elif platform_lower == "linkedin":
            writer = get_linkedin_agent()
        elif platform_lower == "twitter":
            writer = get_twitter_agent()
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        draft_response = writer.run(
            f"Topic: '{topic}'\n\nContext/Research:\n{research_summary}", stream=False
        )
        draft_content = draft_response.content
        if progress_callback:
            progress_callback("social_writer")

        # 3. QA
        print(f"\n[3/3] QA Checking for {platform} compliance...")
        qa_agent = get_social_qa_agent()
        qa_response = qa_agent.run(
            f"Platform: {platform}\nDraft Post:\n{draft_content}\n\nReview and fix if necessary.",
            stream=False,
        )
        final_content = qa_response.content
        if progress_callback:
            progress_callback("social_qa")

        _track_usage(
            name=f"Social_Post_Usage_{platform}",
            input_text=topic,
            output_text=final_content,
            responses=[research_response, draft_response, qa_response],
            metadata={"source": "agno-agent-social", "platform": platform},
        )

        return final_content


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_research_signal(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized or len(normalized) < 40:
        return False
    failure_markers = [
        "cannot proceed", "research was not provided", "missing research",
        "need the research", "no research", "rate limit", "temporarily unavailable",
        "quota", "i apologize", "cannot write the blog", "without the research",
        "please provide the research", "unavailable right now", "try again later",
    ]
    if any(marker in normalized for marker in failure_markers):
        return False
    signal_delimiters = ["\n-", "\n1.", "\nbullet", "\n•", "?", ". "]
    return sum(1 for d in signal_delimiters if d in normalized) > 0


def _structured_fallback_research(subject: str) -> str:
    """Return a deterministic research summary when the research agent fails."""
    sections = [
        f"**Market Snapshot**\n- {subject} is top-of-mind for CMOs focused on profitable growth in 2026.\n"
        f"- Economic pressure pushes teams to prove clear ROI within two quarters.",
        f"**Adoption & Investment**\n- Budgets are shifting toward AI copilots, experimentation platforms, "
        f"and privacy-safe data foundations that accelerate {subject}.",
        f"**Audience Pain Points**\n- Teams struggle with fragmented data, content bottlenecks, and channel saturation.\n"
        f"- Decision makers want faster validation and proof that {subject} drives incremental revenue.",
        f"**People-Also-Ask Style Questions**\n- How does {subject} change day-to-day marketing workflows?\n"
        f"- What KPIs prove success within 90 days?\n"
        f"- How can smaller teams adopt {subject} without enterprise budgets?",
        f"**Opportunities & Next Steps**\n- Pair experimentation frameworks with AI summarization to ship insights weekly.\n"
        f"- Reuse knowledge bases to keep messaging on-brand while scaling {subject} programs.",
    ]
    try:
        kb = get_knowledge_base()
        kb_results = kb.search(subject, limit=3)
        kb_lines = []
        for idx, doc in enumerate(kb_results or [], start=1):
            raw = getattr(doc, "content", "") or ""
            if raw.strip():
                snippet = shorten(raw.replace("\n", " ").strip(), width=280, placeholder="...")
                kb_lines.append(f"- KB Insight {idx}: {snippet}")
        if kb_lines:
            sections.append("**Knowledge Base Highlights**\n" + "\n".join(kb_lines))
    except Exception as kb_exc:
        print(f"[WARN] Could not pull KB fallback insights: {kb_exc}")
    return "\n\n".join(sections)


def _track_usage(*, name: str, input_text: str, output_text: str, responses: list, metadata: dict) -> None:
    """Record aggregate token usage to Langfuse. Silent no-op if Langfuse is not configured."""
    if not langfuse:
        return
    try:
        total_in = sum(
            getattr(r.metrics, "input_tokens", 0)
            for r in responses
            if hasattr(r, "metrics") and r.metrics
        )
        total_out = sum(
            getattr(r.metrics, "output_tokens", 0)
            for r in responses
            if hasattr(r, "metrics") and r.metrics
        )
        gen = langfuse.start_generation(
            name=name,
            model="gemini-flash-latest",
            input=input_text,
            output=output_text,
            usage_details={
                "prompt_tokens": total_in,
                "completion_tokens": total_out,
                "total_tokens": total_in + total_out,
            },
            metadata=metadata,
        )
        gen.end()
    except Exception as exc:
        print(f"[INFO] Could not record Langfuse usage: {exc}")
