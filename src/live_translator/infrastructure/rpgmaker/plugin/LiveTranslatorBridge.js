/*:
 * @target MV MZ
 * @plugindesc Envia texto de diálogo RPG Maker MV/MZ ao RPG Live Translator.
 * @author RPG Live Translator
 *
 * @param Endpoint
 * @text Endpoint
 * @type string
 * @default http://127.0.0.1:8765/rpgmaker/text
 *
 * @help
 * Copie este arquivo para a pasta js/plugins do jogo, habilite-o no Plugin
 * Manager e mantenha o RPG Live Translator rodando em modo RPG Maker MV/MZ.
 */
(() => {
  "use strict";

  const pluginName = "LiveTranslatorBridge";
  const params = PluginManager.parameters(pluginName);
  const endpoint = String(
    params.Endpoint || "http://127.0.0.1:8765/rpgmaker/text"
  );

  function sendText(text) {
    const normalized = String(text || "").trim();
    if (!normalized) {
      return;
    }

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: normalized })
    }).catch(() => {});
  }

  function appendRenderedText(windowMessage, text) {
    windowMessage._liveTranslatorRenderedText =
      (windowMessage._liveTranslatorRenderedText || "") + text;
  }

  function flushRenderedText(windowMessage) {
    const text = String(windowMessage._liveTranslatorRenderedText || "").trim();
    if (text && text !== windowMessage._liveTranslatorLastSentText) {
      windowMessage._liveTranslatorLastSentText = text;
      sendText(text);
    }
    windowMessage._liveTranslatorRenderedText = "";
  }

  const newPage = Window_Message.prototype.newPage;
  Window_Message.prototype.newPage = function(textState) {
    flushRenderedText(this);
    return newPage.call(this, textState);
  };

  const processNormalCharacter = Window_Message.prototype.processNormalCharacter;
  Window_Message.prototype.processNormalCharacter = function(textState) {
    appendRenderedText(this, textState.text[textState.index]);
    return processNormalCharacter.call(this, textState);
  };

  const processNewLine = Window_Message.prototype.processNewLine;
  Window_Message.prototype.processNewLine = function(textState) {
    appendRenderedText(this, "\n");
    return processNewLine.call(this, textState);
  };

  if (Window_Message.prototype.terminateMessage) {
    const terminateMessage = Window_Message.prototype.terminateMessage;
    Window_Message.prototype.terminateMessage = function() {
      flushRenderedText(this);
      return terminateMessage.call(this);
    };
  }

  if (Window_Message.prototype.onEndOfText) {
    const onEndOfText = Window_Message.prototype.onEndOfText;
    Window_Message.prototype.onEndOfText = function() {
      flushRenderedText(this);
      return onEndOfText.call(this);
    };
  }

  const setChoices = Game_Message.prototype.setChoices;
  Game_Message.prototype.setChoices = function(choices, defaultType, cancelType) {
    if (Array.isArray(choices)) {
      choices.forEach(sendText);
    }
    return setChoices.call(this, choices, defaultType, cancelType);
  };
})();
