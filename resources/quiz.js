(function () {
    'use strict';
    var config = window.quizConfig;
    if (!config) return;

    var status = document.getElementById('quiz-save-status');
    var saveTimers = {};

    function collectAnswer(block) {
        var qid = block.dataset.question, type = block.dataset.type;
        if (type === 'MC' || type === 'TF') {
            var checked = block.querySelector('input:checked');
            return checked ? parseInt(checked.value, 10) : null;
        }
        if (type === 'MA') {
            var values = [];
            block.querySelectorAll('input:checked').forEach(function (el) {
                values.push(parseInt(el.value, 10));
            });
            return values.length ? values : null;
        }
        var text = block.querySelector('input[type=text]');
        return text && text.value.trim() !== '' ? text.value : null;
    }

    function save(block) {
        var qid = block.dataset.question;
        var answer = collectAnswer(block);
        fetch(config.saveUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json',
                      'X-CSRFToken': config.csrfToken},
            body: JSON.stringify({question: parseInt(qid, 10),
                                  answer: answer}),
        }).then(function (response) {
            if (!response.ok) throw new Error('save failed');
            status.textContent = '';
            var map = document.getElementById('map-' + qid);
            if (map) map.classList.toggle('answered', answer !== null);
        }).catch(function () {
            status.textContent = 'Save failed — retrying…';
            clearTimeout(saveTimers[qid]);
            saveTimers[qid] = setTimeout(function () { save(block); }, 3000);
        });
    }

    document.querySelectorAll('.quiz-question').forEach(function (block) {
        block.addEventListener('change', function () { save(block); });
        var text = block.querySelector('input[type=text]');
        if (text) {
            text.addEventListener('input', function () {
                clearTimeout(saveTimers['t' + block.dataset.question]);
                saveTimers['t' + block.dataset.question] =
                    setTimeout(function () { save(block); }, 800);
            });
        }
    });

    if (config.timeRemaining !== null) {
        var timerEl = document.getElementById('quiz-timer');
        var deadline = Date.now() + config.timeRemaining * 1000;
        (function tick() {
            var left = Math.max(0, Math.round(
                (deadline - Date.now()) / 1000));
            var minutes = Math.floor(left / 60),
                seconds = left % 60;
            timerEl.textContent = minutes + ':' +
                (seconds < 10 ? '0' : '') + seconds;
            timerEl.className = left < 60 ? 'danger' :
                (left < 300 ? 'warning' : '');
            if (left <= 0) {
                document.getElementById('quiz-submit-form')
                    .submit();
                return;
            }
            setTimeout(tick, 500);
        })();
    }
}());
