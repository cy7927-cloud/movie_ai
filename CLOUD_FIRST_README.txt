Cloud open-weight director-learning adapter / 云端导演学习模型适配器
============================================================
1. No external network calls by default. No video-generation model is used.
2. Real model calls require a service-issued token, explicit run command and service-specific quotas.
3. First read: 云端开源导演模型_实际试验记录.md
4. View sample locally without API key:
   python cloud_director_inference.py prepare --task LESSON_LESSON_01
5. After confirming a free allotment and granting permission to send selected film stills:
   set GROQ_API_KEY=...   (Windows cmd)
   export GROQ_API_KEY=... (Linux/macOS)
   python cloud_director_inference.py run --provider groq --task LESSON_LESSON_01
6. 2026-11-14 actual public demos: 403 / submitted but no answer / submitted but no answer.
   Do not claim successful real cloud inference from these tests.
