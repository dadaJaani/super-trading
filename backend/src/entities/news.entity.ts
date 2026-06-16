import { Column, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('news')
export class News {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column('timestamptz', { nullable: true })
  time: Date | null;

  @Column('text', { nullable: true })
  source: string | null;

  @Column('text', { nullable: true })
  headline: string | null;

  @Column('decimal', { name: 'sentiment_score', nullable: true })
  sentimentScore: string | null;

  @Column('text', { array: true, nullable: true })
  instruments: string[] | null;

  @Column('jsonb', { name: 'raw_response', nullable: true })
  rawResponse: Record<string, unknown> | null;
}
