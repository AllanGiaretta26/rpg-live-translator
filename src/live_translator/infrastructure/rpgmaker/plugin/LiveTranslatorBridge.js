/*:
 * @target MV MZ
 * @plugindesc Sends RPG Maker MV/MZ dialogue text to RPG Live Translator.
 * @author RPG Live Translator
 *
 * @param Endpoint
 * @text Endpoint
 * @type string
 * @default http://127.0.0.1:8765/rpgmaker/text
 *
 * @help
 * Copy this file to the game's js/plugins folder, enable it in Plugin Manager,
 * and keep RPG Live Translator running in RPG Maker MV/MZ mode.
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

  const addMessage = Game_Message.prototype.add;
  Game_Message.prototype.add = function(text) {
    sendText(text);
    return addMessage.call(this, text);
  };

  const setChoices = Game_Message.prototype.setChoices;
  Game_Message.prototype.setChoices = function(choices, defaultType, cancelType) {
    if (Array.isArray(choices)) {
      choices.forEach(sendText);
    }
    return setChoices.call(this, choices, defaultType, cancelType);
  };
})();
