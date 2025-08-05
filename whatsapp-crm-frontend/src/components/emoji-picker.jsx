// src/components/emoji-picker.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Smile } from 'lucide-react';
import data from '@emoji-mart/data';
import Picker from '@emoji-mart/react';

export function EmojiPicker({ onSelect }) {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef(null);

  const handleEmojiSelect = (emoji) => {
    onSelect(emoji.native);
    setIsOpen(false);
  };

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (popoverRef.current && !popoverRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="rounded-full p-2 hover:bg-muted transition-colors"
          onClick={() => setIsOpen(!isOpen)}
        >
          <Smile className="h-5 w-5 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent 
        ref={popoverRef}
        className="w-auto p-0 border-0 shadow-lg"
        align="start"
      >
        <Picker
          data={data}
          onEmojiSelect={handleEmojiSelect}
          theme="light"
          previewPosition="none"
          searchPosition="none"
          skinTonePosition="none"
          perLine={8}
          emojiSize={24}
          emojiButtonSize={36}
          navPosition="none"
          dynamicWidth={true}
        />
      </PopoverContent>
    </Popover>
  );
}