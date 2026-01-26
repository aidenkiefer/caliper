"use client";

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { glossaryTerms, getTermsByCategory, searchTerms, type GlossaryTerm } from '@/lib/glossary';
import { Search } from 'lucide-react';

const categories: Array<{ id: GlossaryTerm['category']; label: string; icon: string }> = [
  { id: 'performance', label: 'Performance Metrics', icon: '📊' },
  { id: 'risk', label: 'Risk Metrics', icon: '⚠️' },
  { id: 'position', label: 'Position Terms', icon: '📈' },
  { id: 'strategy', label: 'Strategy Terms', icon: '🤖' },
];

export default function HelpPage() {
  const [searchQuery, setSearchQuery] = useState('');
  
  const displayTerms = searchQuery 
    ? searchTerms(searchQuery)
    : glossaryTerms;
  
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Help & Glossary</h1>
        <p className="text-muted-foreground mt-2">
          Learn about trading terminology and platform features
        </p>
      </div>
      
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search terms..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>
      
      {/* Results */}
      {searchQuery ? (
        <Card>
          <CardHeader>
            <CardTitle>Search Results ({displayTerms.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <TermList terms={displayTerms} />
          </CardContent>
        </Card>
      ) : (
        /* Category Sections */
        <div className="grid gap-6">
          {categories.map(category => (
            <Card key={category.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span>{category.icon}</span>
                  {category.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <TermList terms={getTermsByCategory(category.id)} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function TermList({ terms }: { terms: GlossaryTerm[] }) {
  if (terms.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-4">
        No terms found
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {terms.map(term => (
        <div key={term.term} className="border-b pb-4 last:border-0">
          <dt className="font-semibold text-foreground">{term.term}</dt>
          <dd className="text-muted-foreground mt-1">{term.definition}</dd>
          {term.example && (
            <dd className="text-sm text-muted-foreground mt-1 italic">
              Example: {term.example}
            </dd>
          )}
        </div>
      ))}
    </div>
  );
}
