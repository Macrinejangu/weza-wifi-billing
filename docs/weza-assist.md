# Weza Assist

The customer portal shows the AI chat bubble before and after sign-in. The existing Support page still lists the original help topics. Weza Assist reads the same saved FAQs, follows up on the current conversation, and links to its sources. The website publishes the support details used for the email, call, and WhatsApp buttons.

## Local demo

1. Start Ollama on the machine running the API. Install the lightweight demo model with `ollama pull qwen2.5:0.5b`.
2. Set `WEZA_ASSIST_MODEL=qwen2.5:0.5b` for the backend and restart the API. Ollama should listen at `127.0.0.1:11434`. Keep the model service on loopback.
3. Open the customer portal and choose Weza Assist. Ask what to do after paying when internet is still unavailable. Follow up by asking whether to pay again. Ask an unrelated question to check the handoff.

The demo uses a local model and needs no paid API key. The first answer may take longer while Ollama loads the model.

## Sources and handoff

FAQ changes in System Settings are available on the next chat turn. The chatbot also comes with a linked Safaricom safety reference. Add more approved sources through `WEZA_ASSIST_RESOURCES`, a JSON list of up to five objects containing a `title` and either approved plain `text` or a public HTML `url`. To use a PDF, supply its approved text and the source link. Entries with a URL only are read from the website and cached for up to 15 minutes. The server reads HTTPS pages on Weza and Safaricom’s approved domains. It never sends a customer's question to those sites.

The chatbot does not look up accounts, trigger payments, or request passwords or M-Pesa PINs. Unsupported questions or a model failure show the support contact links. Before public handover, verify the unpaid hotspot reaches the portal and chat endpoint, and agree who operates the model host and handles support. Apply request limits at the public gateway.
