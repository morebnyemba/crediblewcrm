import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { apiCall } from '@/lib/api';
import { format } from 'date-fns';

// UI Components
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { FiCalendar, FiMapPin, FiPlus, FiEdit, FiTrash2 } from 'react-icons/fi';

const EventCard = ({ event, onEdit, onDelete }) => {
  const eventDate = event.start_time ? new Date(event.start_time) : null;
  const formattedDate = eventDate ? format(eventDate, 'PPP') : 'Date not set';
  const formattedTime = eventDate ? format(eventDate, 'p') : '';

  return (
    <Card className="flex flex-col h-full dark:bg-slate-800 transition-shadow hover:shadow-lg">
      <CardHeader>
        <CardTitle className="text-lg">{event.title}</CardTitle>
        <CardDescription>
          <div className="flex items-center text-sm text-muted-foreground mt-1">
            <FiCalendar className="mr-2 h-4 w-4 flex-shrink-0" />
            <span>{formattedDate} at {formattedTime}</span>
          </div>
          {event.location && (
            <div className="flex items-center text-sm text-muted-foreground mt-1">
              <FiMapPin className="mr-2 h-4 w-4 flex-shrink-0" />
              <span>{event.location}</span>
            </div>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-grow">
        <p className="text-sm text-muted-foreground line-clamp-3">
          {event.description || 'No description available.'}
        </p>
      </CardContent>
      <CardFooter className="flex justify-end pt-4">
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={() => onEdit(event.id)}><FiEdit className="h-4 w-4 text-muted-foreground" /></Button>
          <Button variant="ghost" size="icon" onClick={() => onDelete(event.id)}><FiTrash2 className="h-4 w-4 text-destructive" /></Button>
        </div>
      </CardFooter>
    </Card>
  );
};

export default function EventsPage() {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const fetchEvents = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiCall(`/crm-api/church-services/events/`);
      setEvents(data.results || []);
    } catch (error) {
      toast.error("Failed to load events.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleDelete = async (eventId) => {
    if (!window.confirm("Are you sure you want to delete this event?")) return;
    try {
      await apiCall(`/crm-api/church-services/events/${eventId}/`, 'DELETE');
      toast.success("Event deleted successfully.");
      setEvents(prev => prev.filter(e => e.id !== eventId));
    } catch (error) {
      toast.error("Failed to delete event.");
    }
  };

  return (
    <div className="space-y-8 p-4 md:p-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Upcoming Events</h1>
          <p className="text-muted-foreground">Manage your church's events.</p>
        </div>
        <Button onClick={() => navigate('/events/new')}><FiPlus className="mr-2 h-4 w-4" /> Create Event</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? ([...Array(3)].map((_, i) => <Card key={i}><CardHeader><Skeleton className="h-6 w-3/4" /></CardHeader><CardContent><Skeleton className="h-4 w-full" /></CardContent></Card>)) : events.length > 0 ? (events.map(event => <EventCard key={event.id} event={event} onEdit={() => navigate(`/events/edit/${event.id}`)} onDelete={handleDelete} />)) : (<p className="col-span-full text-center">No events found.</p>)}
      </div>
    </div>
  );
}