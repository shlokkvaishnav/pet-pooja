import { useState, useEffect } from 'react';

const TypewriterText = ({
    baseText = '',
    words = [],
    typeDelay = 50,
    deleteDelay = 30,
    pauseTime = 1500,
    start = false,
    className,
    cursorClassName
}) => {
    const [displayedText, setDisplayedText] = useState('');
    const [started, setStarted] = useState(false);

    // States to manage the typing sequence
    const [phase, setPhase] = useState('pending'); // pending -> base -> typing -> pausing -> deleting -> typing -> ... -> done
    const [wordIndex, setWordIndex] = useState(0);

    // Trigger start
    useEffect(() => {
        if (start && !started) {
            setStarted(true);
            if (baseText) {
                setPhase('base');
            } else if (words.length > 0) {
                setPhase('typing');
            } else {
                setPhase('done');
            }
        }
    }, [start, started, baseText, words]);

    useEffect(() => {
        if (!started || phase === 'done' || phase === 'pending') return;

        let timeout;

        // Phase 1: Type the base text
        if (phase === 'base') {
            if (displayedText.length < baseText.length) {
                timeout = setTimeout(() => {
                    setDisplayedText(baseText.slice(0, displayedText.length + 1));
                }, typeDelay);
            } else {
                if (words.length > 0) {
                    setPhase('typing');
                } else {
                    setPhase('done');
                }
            }
        }
        // Phase 2: Type the current varying word
        else if (phase === 'typing') {
            const targetWord = words[wordIndex];
            const currentFullText = baseText + targetWord;

            if (displayedText.length < currentFullText.length) {
                timeout = setTimeout(() => {
                    setDisplayedText(currentFullText.slice(0, displayedText.length + 1));
                }, typeDelay);
            } else {
                // Finished typing the target word
                if (wordIndex < words.length - 1) {
                    setPhase('pausing');
                } else {
                    setPhase('done');
                }
            }
        }
        // Phase 3: Pause before deleting
        else if (phase === 'pausing') {
            timeout = setTimeout(() => {
                setPhase('deleting');
            }, pauseTime);
        }
        // Phase 4: Delete the current word back to base text
        else if (phase === 'deleting') {
            if (displayedText.length > baseText.length) {
                timeout = setTimeout(() => {
                    setDisplayedText(displayedText.slice(0, -1));
                }, deleteDelay);
            } else {
                // Finished deleting, move to next word
                setWordIndex(prev => prev + 1);
                setPhase('typing');
            }
        }

        return () => clearTimeout(timeout);
    }, [displayedText, phase, started, baseText, words, wordIndex, typeDelay, deleteDelay, pauseTime]);

    // Hide cursor if we reached the end
    const showCursor = started && phase !== 'done';

    return (
        <span className={className}>
            {displayedText}
            {showCursor && <span className={cursorClassName || "cursor"}></span>}
        </span>
    );
};

export default TypewriterText;
