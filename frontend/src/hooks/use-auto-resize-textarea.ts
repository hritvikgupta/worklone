import { useRef, useEffect } from "react";

export function useAutoResizeTextarea({
  minHeight,
  maxHeight,
}: {
  minHeight: number;
  maxHeight: number;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function adjustHeight(force?: boolean) {
    const textarea = textareaRef.current;
    if (!textarea) return;

    if (force) {
      textarea.style.height = `${minHeight}px`;
      return;
    }

    textarea.style.height = "auto";
    const newHeight = Math.min(
      Math.max(textarea.scrollHeight, minHeight),
      maxHeight
    );
    textarea.style.height = `${newHeight}px`;
  }

  useEffect(() => {
    adjustHeight();
  }, []);

  return { textareaRef, adjustHeight };
}
