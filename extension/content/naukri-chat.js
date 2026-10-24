// Naukri asks its questions in a chat drawer after Apply. Each one is answered from the Answer Bank.
(() => {
  const JSA = (window.JSA = window.JSA || {});
  const SENT = /successfully applied|you have applied|application (sent|submitted)/i;
  const DRAWER = ".chatbot_DrawerContentWrapper, [class*='chatbot_Drawer']";

  const labelFor = (box) => {
    const own = box.id && document.querySelector(`label[for="${CSS.escape(box.id)}"]`);
    return JSA.clean(own ? own.innerText : (box.closest("label") || {}).innerText || box.value);
  };

  JSA.naukriChat = async (job) => {
    const answers = [];
    let asked = "";
    for (let round = 0; round < 12; round++) {
      await JSA.pause(1.5, 3);
      if (SENT.test(JSA.text())) return { status: "submitted", message: "Submitted.", answers, signedIn: true };
      const drawer = document.querySelector(DRAWER);
      if (!drawer || !JSA.shown(drawer)) continue;
      const messages = drawer.querySelectorAll(".botMsg, [class*='botMsg']");
      const question = messages.length ? JSA.clean(messages[messages.length - 1].innerText) : "";
      if (!question || question === asked) continue;
      asked = question;
      const boxes = [...drawer.querySelectorAll("input[type=radio], input[type=checkbox]")];
      const labels = boxes.map(labelFor);
      const reply = await JSA.ask({ type: "answer", jobId: job.id, question, options: labels, required: true });
      if (reply.answer == null) {
        return { status: "needs_answer", message: `Waiting for your answer to: ${question} (the Naukri application is not complete)`, answers, signedIn: true };
      }
      let answer = reply.answer;
      if (boxes.length) {
        const chosen = JSA.pick(labels, answer);
        if (chosen == null) return { status: "needs_answer", message: `Your answer doesn't match Naukri's options for: ${question}`, answers, signedIn: true };
        JSA.check(boxes[labels.indexOf(chosen)]);
        answer = chosen;
      } else {
        const box = drawer.querySelector("[contenteditable='true'], .chatbot_InputContainer input, .chatbot_InputContainer textarea");
        if (!box) return { status: "failed", message: `Couldn't find where to type the answer to: ${question}`, answers, signedIn: true };
        JSA.setValue(box, answer);
      }
      answers.push({ question, answer, how: reply.how });
      await JSA.pause(0.8, 2);
      const send = drawer.querySelector(".sendMsg, [class*='sendMsg']") || JSA.button(/^(save|submit|send)$/i, drawer);
      send?.click();
    }
    return { status: "unconfirmed", message: "Applied on Naukri, but the questions didn't finish. Check the job on Naukri.", answers, signedIn: true };
  };
})();
