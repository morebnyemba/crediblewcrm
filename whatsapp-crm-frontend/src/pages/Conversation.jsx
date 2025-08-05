// src/pages/ConversationsPage.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAtom } from 'jotai';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  FiSend, FiUsers, FiMessageSquare, FiSearch, 
  FiLoader, FiAlertCircle, FiPaperclip, 
  FiArrowLeft, FiCheck, FiClock, FiMoreVertical,
  FiChevronRight
} from 'react-icons/fi';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { apiCall } from '@/lib/api';
import { selectedContactAtom } from '@/atoms/conversationAtoms';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useDebounce } from 'use-debounce';

const MessageBubble = ({ message, contactName, isLast }) => {
  const isOutgoing = message.direction === 'out';
  const bubbleClass = isOutgoing 
    ? 'bg-primary text-primary-foreground rounded-se-none' 
    : 'bg-muted text-foreground rounded-ss-none';

  const statusIcons = {
    sent: <FiCheck className="h-3 w-3 text-muted-foreground" />,
    delivered: <div className="flex gap-0.5"><FiCheck className="h-3 w-3 text-muted-foreground" /><FiCheck className="h-3 w-3 text-muted-foreground -ml-1" /></div>,
    read: <div className="flex gap-0.5"><FiCheck className="h-3 w-3 text-blue-500" /><FiCheck className="h-3 w-3 text-blue-500 -ml-1" /></div>,
    failed: <FiAlertCircle className="h-3 w-3 text-destructive" />,
    pending: <FiClock className="h-3 w-3 text-muted-foreground animate-pulse" />
  };

  return (
    <div className={`flex flex-col my-1.5 ${isOutgoing ? 'items-end' : 'items-start'}`}>
      <div className={`max-w-[85%] px-3 py-2 rounded-xl shadow-sm ${bubbleClass}`}>
        <p className="text-sm whitespace-pre-wrap">{message.content_preview || message.text_content || "Unsupported message"}</p>
      </div>
      <div className={`flex items-center gap-1 mt-1 px-1 ${isOutgoing ? 'flex-row-reverse' : ''}`}>
        <span className="text-xs text-muted-foreground">
          {message.timestamp ? formatDistanceToNow(parseISO(message.timestamp), { addSuffix: true }) : 'Sending...'}
        </span>
        {isOutgoing && message.status && (
          <span className={isLast ? 'opacity-100' : 'opacity-0'}>
            {statusIcons[message.status] || null}
          </span>
        )}
      </div>
    </div>
  );
};

const ContactListItem = React.memo(({ contact, isSelected, onSelect, hasUnread }) => {
  return (
    <div
      onClick={() => onSelect(contact)}
      className={`p-3 cursor-pointer transition-colors ${
        isSelected 
          ? 'bg-accent border-l-4 border-primary' 
          : 'hover:bg-muted/50'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="relative">
          <Avatar className="h-10 w-10">
            <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(contact.name || contact.whatsapp_id)}&background=random`} />
            <AvatarFallback>{contact.name?.substring(0,2) || 'CN'}</AvatarFallback>
          </Avatar>
          {hasUnread && (
            <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-primary border-2 border-background" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="font-medium truncate">{contact.name || contact.whatsapp_id}</p>
            <FiChevronRight className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {contact.last_message_preview || 'No messages yet'}
          </p>
        </div>
      </div>
    </div>
  );
});

export default function ConversationsPage() {
  const [contacts, setContacts] = useState([]);
  const [selectedContact, setSelectedContact] = useAtom(selectedContactAtom);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState({
    contacts: true,
    messages: false
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm] = useDebounce(searchTerm, 300);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const contactsScrollRef = useRef(null);
  const messagesScrollRef = useRef(null);

  const fetchContacts = useCallback(async (search = '') => {
    setIsLoading(prev => ({ ...prev, contacts: true }));
    try {
      const data = await apiCall(
        `/crm-api/conversations/contacts/?search=${encodeURIComponent(search)}`,
        'GET'
      );
      setContacts(data.results || []);
    } catch (error) {
      toast.error("Couldn't load contacts");
    } finally {
      setIsLoading(prev => ({ ...prev, contacts: false }));
    }
  }, []);

  const fetchMessages = useCallback(async (contactId) => {
    if (!contactId) return;
    setIsLoading(prev => ({ ...prev, messages: true }));
    try {
      const data = await apiCall(
        `/crm-api/conversations/contacts/${contactId}/messages/`,
        'GET'
      );
      setMessages(data.results?.reverse() || []);
    } catch (error) {
      toast.error("Couldn't load messages");
    } finally {
      setIsLoading(prev => ({ ...prev, messages: false }));
    }
  }, []);

  useEffect(() => {
    fetchContacts(debouncedSearchTerm);
  }, [debouncedSearchTerm, fetchContacts]);

  useEffect(() => {
    if (selectedContact) {
      fetchMessages(selectedContact.id);
      inputRef.current?.focus();
    }
  }, [selectedContact, fetchMessages]);

  useEffect(() => {
    if (messagesScrollRef.current) {
      messagesScrollRef.current.scrollTo({
        top: messagesScrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedContact) return;

    const tempId = `temp-${Date.now()}`;
    const optimisticMessage = {
      id: tempId,
      contact: selectedContact.id,
      direction: 'out',
      text_content: newMessage,
      timestamp: new Date().toISOString(),
      status: 'pending'
    };

    setMessages(prev => [...prev, optimisticMessage]);
    setNewMessage('');

    try {
      const sentMessage = await apiCall(
        '/crm-api/conversations/messages/',
        'POST',
        {
          contact: selectedContact.id,
          message_type: 'text',
          content_payload: { body: newMessage }
        }
      );

      setMessages(prev => prev.map(msg => 
        msg.id === tempId ? { ...sentMessage, timestamp: sentMessage.timestamp || optimisticMessage.timestamp } : msg
      ));
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === tempId ? { ...msg, status: 'failed' } : msg
      ));
      toast.error("Message failed to send");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  return (
    <div className="flex h-[calc(100vh-var(--header-height))] overflow-hidden">
      {/* Conversations Panel */}
      <div className={`
        ${selectedContact ? 'hidden md:flex md:w-96' : 'flex w-full'} 
        border-r flex-col bg-background transition-all duration-300
      `}>
        <div className="p-3 border-b sticky top-0 bg-background z-10">
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search contacts..."
              className="pl-9"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        
        <ScrollArea 
          ref={contactsScrollRef}
          className="flex-1 h-full"
        >
          {isLoading.contacts ? (
            <div className="space-y-2 p-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-3 p-3">
                  <div className="h-10 w-10 rounded-full bg-muted animate-pulse" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 bg-muted rounded animate-pulse" />
                    <div className="h-3 w-1/2 bg-muted rounded animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
          ) : contacts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full p-6 text-center">
              <FiUsers className="h-12 w-12 mb-4 text-muted-foreground/30" />
              <p className="text-muted-foreground">No contacts found</p>
              <p className="text-sm text-muted-foreground/70 mt-1">
                {searchTerm ? 'Try a different search' : 'Start by adding contacts'}
              </p>
            </div>
          ) : (
            contacts.map(contact => (
              <ContactListItem
                key={contact.id}
                contact={contact}
                isSelected={selectedContact?.id === contact.id}
                onSelect={setSelectedContact}
                hasUnread={contact.unread_count > 0}
              />
            ))
          )}
        </ScrollArea>
      </div>

      {/* Messages Panel */}
      {selectedContact ? (
        <div className="flex-1 flex flex-col bg-background">
          <div className="p-3 border-b flex items-center justify-between sticky top-0 bg-background z-10">
            <div className="flex items-center gap-3">
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => setSelectedContact(null)}
              >
                <FiArrowLeft className="h-5 w-5" />
              </Button>
              <Avatar>
                <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(selectedContact.name || selectedContact.whatsapp_id)}`} />
                <AvatarFallback>{selectedContact.name?.substring(0,2) || 'CN'}</AvatarFallback>
              </Avatar>
              <div>
                <h2 className="font-semibold">{selectedContact.name || selectedContact.whatsapp_id}</h2>
                <p className="text-xs text-muted-foreground">
                  {selectedContact.last_seen ? 
                    `Active ${formatDistanceToNow(parseISO(selectedContact.last_seen), { addSuffix: true })}` : 
                    'Offline'}
                </p>
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <FiMoreVertical className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>View profile</DropdownMenuItem>
                <DropdownMenuItem>Mark as unread</DropdownMenuItem>
                <DropdownMenuItem className="text-destructive">Delete chat</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          
          <ScrollArea 
            ref={messagesScrollRef}
            className="flex-1 p-4"
          >
            {isLoading.messages ? (
              <div className="flex justify-center items-center h-full">
                <FiLoader className="animate-spin h-6 w-6 text-muted-foreground" />
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <FiMessageSquare className="h-12 w-12 mb-4 opacity-30" />
                <h3 className="text-lg font-medium">No messages yet</h3>
                <p className="text-sm mt-1">Send your first message to {selectedContact.name || 'this contact'}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((msg, i) => (
                  <MessageBubble 
                    key={msg.id} 
                    message={msg} 
                    contactName={selectedContact.name}
                    isLast={i === messages.length - 1}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </ScrollArea>

          <div className="p-3 border-t bg-background sticky bottom-0">
            <form onSubmit={handleSendMessage} className="flex items-end gap-2">
              <Button 
                type="button" 
                variant="ghost" 
                size="icon"
                className="text-muted-foreground"
              >
                <FiPaperclip className="h-5 w-5" />
              </Button>
              <Textarea
                ref={inputRef}
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message..."
                rows={1}
                className="flex-1 py-3 min-h-[44px] max-h-[120px] overflow-y-auto resize-none"
              />
              <Button 
                type="submit" 
                size="sm" 
                disabled={!newMessage.trim()}
                className="h-[44px]"
              >
                <FiSend className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </div>
      ) : (
        <div className="hidden md:flex flex-1 flex-col items-center justify-center p-10 text-center text-muted-foreground">
          <FiMessageSquare className="h-24 w-24 mb-4 opacity-20" />
          <h3 className="text-xl font-medium mb-2">Select a conversation</h3>
          <p className="max-w-md text-sm">
            Choose from your existing conversations or start a new one
          </p>
        </div>
      )}
    </div>
  );
}