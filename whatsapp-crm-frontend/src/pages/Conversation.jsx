// src/pages/ConversationsPage.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAtom } from 'jotai';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  FiSend, 
  FiUser, 
  FiUsers, 
  FiMessageSquare, 
  FiSearch, 
  FiLoader, 
  FiAlertCircle, 
  FiPaperclip, 
  FiSmile, 
  FiArrowLeft,
  FiCheck,
  FiClock,
  FiMoreVertical
} from 'react-icons/fi';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { apiCall } from '@/lib/api';
import { selectedContactAtom } from '@/atoms/conversationAtoms';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const MessageBubble = ({ message, contactName }) => {
  const isOutgoing = message.direction === 'out';
  const alignClass = isOutgoing ? 'items-end' : 'items-start';
  const bubbleClass = isOutgoing 
    ? 'bg-primary text-white rounded-tr-none' 
    : 'bg-muted text-foreground rounded-tl-none';
  
  const statusIcon = {
    sent: <FiCheck className="h-3 w-3 text-muted-foreground" />,
    delivered: <FiCheck className="h-3 w-3 text-muted-foreground" />,
    read: <FiCheck className="h-3 w-3 text-blue-500" />,
    failed: <FiAlertCircle className="h-3 w-3 text-red-500" />,
    pending: <FiClock className="h-3 w-3 text-muted-foreground animate-pulse" />
  };

  const content = message.content_preview || message.text_content || "Unsupported message type";

  return (
    <div className={`flex flex-col my-1.5 ${alignClass}`}>
      <div className={`max-w-[80%] px-3 py-2 rounded-xl shadow-sm ${bubbleClass}`}>
        <p className="text-sm whitespace-pre-wrap">{content}</p>
      </div>
      <div className="flex items-center gap-1 mt-1 px-1">
        <span className="text-xs text-muted-foreground">
          {isOutgoing ? "You" : contactName || message.contact_details?.name}
          {' · '}
          {message.timestamp ? formatDistanceToNow(parseISO(message.timestamp), { addSuffix: true }) : 'sending...'}
        </span>
        {isOutgoing && message.status && (
          <span className="text-xs">
            {statusIcon[message.status] || null}
          </span>
        )}
      </div>
    </div>
  );
};

const ContactListItem = ({ contact, isSelected, onSelect }) => {
  const lastSeenText = contact.last_seen 
    ? formatDistanceToNow(parseISO(contact.last_seen), { addSuffix: true })
    : 'Never';

  return (
    <div
      onClick={() => onSelect(contact)}
      className={`p-3 border-b cursor-pointer transition-colors
        ${isSelected 
          ? 'bg-accent border-l-4 border-primary' 
          : 'hover:bg-muted/50'}`}
    >
      <div className="flex items-center gap-3">
        <Avatar className="h-10 w-10">
          <AvatarImage 
            src={`https://ui-avatars.com/api/?name=${encodeURIComponent(contact.name || contact.whatsapp_id)}&background=random`} 
            alt={contact.name} 
          />
          <AvatarFallback>
            {(contact.name || contact.whatsapp_id || 'U').substring(0,2).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="font-medium truncate">{contact.name || contact.whatsapp_id}</p>
            {contact.unread_count > 0 && (
              <Badge variant="default" className="h-5 w-5 p-0 flex items-center justify-center">
                {contact.unread_count > 9 ? '9+' : contact.unread_count}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <p className="text-xs text-muted-foreground truncate">
              {lastSeenText}
            </p>
            {contact.needs_human_intervention && (
              <Badge variant="destructive" className="text-xs px-1.5 py-0.5">
                Needs Help
              </Badge>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default function ConversationsPage() {
  const [contacts, setContacts] = useState([]);
  const [selectedContact, setSelectedContact] = useAtom(selectedContactAtom);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoadingContacts, setIsLoadingContacts] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const messagesEndRef = useRef(null);

  const fetchContacts = useCallback(async (search = '') => {
    setIsLoadingContacts(true);
    try {
      const endpoint = search 
        ? `/crm-api/conversations/contacts/?search=${encodeURIComponent(search)}` 
        : '/crm-api/conversations/contacts/';
      const data = await apiCall(endpoint, 'GET', null, true);
      setContacts(data.results || []);
    } catch (error) {
      toast.error("Failed to fetch contacts.");
    } finally {
      setIsLoadingContacts(false);
    }
  }, []);

  const fetchMessagesForContact = useCallback(async (contactId) => {
    if (!contactId) return;
    setIsLoadingMessages(true);
    setMessages([]);
    try {
      const data = await apiCall(
        `/crm-api/conversations/contacts/${contactId}/messages/`, 
        'GET', 
        null, 
        true
      );
      setMessages((data.results || []).reverse());
    } catch (error) {
      toast.error("Failed to fetch messages for this contact.");
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  useEffect(() => {
    if (selectedContact) {
      fetchMessagesForContact(selectedContact.id);
    }
  }, [selectedContact, fetchMessagesForContact]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedContact) return;

    setIsSendingMessage(true);
    const tempMessageId = `temp_${Date.now()}`;

    const optimisticMessage = {
      id: tempMessageId,
      contact: selectedContact.id,
      direction: 'out',
      message_type: 'text',
      text_content: newMessage,
      content_payload: { body: newMessage, preview_url: false },
      timestamp: new Date().toISOString(),
      status: 'pending',
    };
    
    setMessages(prev => [...prev, optimisticMessage]);
    setNewMessage('');

    try {
      const payload = {
        contact: selectedContact.id,
        message_type: 'text',
        content_payload: { body: optimisticMessage.text_content, preview_url: false },
      };
      
      const sentMessage = await apiCall(
        '/crm-api/conversations/messages/', 
        'POST', 
        payload
      );
      
      setMessages(prev => prev.map(msg => 
        msg.id === tempMessageId 
          ? {...sentMessage, timestamp: sentMessage.timestamp || optimisticMessage.timestamp} 
          : msg
      ));
      
      toast.success("Message sent successfully!");
    } catch (error) {
      toast.error(`Failed to send message: ${error.message}`);
      setMessages(prev => prev.map(msg => 
        msg.id === tempMessageId 
          ? {...msg, status: 'failed', error_details: {detail: error.message}} 
          : msg
      ));
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    fetchContacts(e.target.value);
  };

  return (
    <div className="flex h-[calc(100vh-var(--header-height,4rem))] overflow-hidden">
      {/* Contacts List Panel */}
      <div className={`
        w-full md:w-96 border-r flex flex-col bg-background
        ${selectedContact ? 'hidden md:flex' : 'flex'}
      `}>
        <div className="p-3 border-b">
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input 
              type="search" 
              placeholder="Search contacts..." 
              className="pl-9"
              value={searchTerm}
              onChange={handleSearchChange}
            />
          </div>
        </div>
        
        <ScrollArea className="flex-1">
          {isLoadingContacts && contacts.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              <FiLoader className="animate-spin h-6 w-6 mx-auto my-3" /> 
              Loading contacts...
            </div>
          ) : contacts.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No contacts found
            </div>
          ) : (
            contacts.map(contact => (
              <ContactListItem
                key={contact.id}
                contact={contact}
                isSelected={selectedContact?.id === contact.id}
                onSelect={setSelectedContact}
              />
            ))
          )}
        </ScrollArea>
      </div>

      {/* Message Display and Input Panel */}
      <div className={`
        flex-1 flex flex-col bg-background
        ${selectedContact ? 'flex' : 'hidden md:flex'}
      `}>
        {selectedContact ? (
          <>
            <div className="p-3 border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="md:hidden" 
                  onClick={() => setSelectedContact(null)}
                >
                  <FiArrowLeft className="h-5 w-5" />
                </Button>
                <Avatar>
                  <AvatarImage 
                    src={`https://ui-avatars.com/api/?name=${encodeURIComponent(selectedContact.name || selectedContact.whatsapp_id)}&background=random`} 
                    alt={selectedContact.name} 
                  />
                  <AvatarFallback>
                    {(selectedContact.name || selectedContact.whatsapp_id || 'U').substring(0,2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="font-semibold">{selectedContact.name || selectedContact.whatsapp_id}</h2>
                  <p className="text-xs text-muted-foreground">
                    {selectedContact.whatsapp_id}
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
                  <DropdownMenuItem>
                    View Contact Details
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    Mark as Resolved
                  </DropdownMenuItem>
                  <DropdownMenuItem className="text-destructive">
                    Delete Conversation
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            
            <ScrollArea className="flex-1 p-4 space-y-3 bg-muted/20">
              {isLoadingMessages ? (
                <div className="text-center p-4">
                  <FiLoader className="animate-spin h-6 w-6 mx-auto my-3" /> 
                  Loading messages...
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <FiMessageSquare className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg font-medium">No messages yet</p>
                  <p className="text-sm">Start a conversation with {selectedContact.name || 'this contact'}</p>
                </div>
              ) : (
                messages.map(msg => (
                  <MessageBubble 
                    key={msg.id} 
                    message={msg} 
                    contactName={selectedContact.name} 
                  />
                ))
              )}
              <div ref={messagesEndRef} />
            </ScrollArea>

            <form 
              onSubmit={handleSendMessage} 
              className="p-3 border-t flex items-center gap-2 bg-background"
            >
              <Button variant="ghost" size="icon" type="button">
                <FiPaperclip className="h-5 w-5 text-muted-foreground"/>
              </Button>
              <Input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Type a message..."
                className="flex-1"
                autoComplete="off"
              />
              <Button 
                type="submit" 
                disabled={isSendingMessage || !newMessage.trim()}
                className="gap-2"
              >
                {isSendingMessage ? (
                  <FiLoader className="animate-spin h-4 w-4" />
                ) : (
                  <FiSend className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">Send</span>
              </Button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-10 text-center text-muted-foreground">
            <FiMessageSquare className="h-24 w-24 mb-4 opacity-30" />
            <h3 className="text-xl font-medium mb-2">No conversation selected</h3>
            <p className="max-w-md">
              Select a contact from the list to view messages or start a new conversation.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}